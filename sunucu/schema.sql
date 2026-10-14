-- KidOn "Ebeveyn telefonu" sunucu şeması (Supabase / Postgres).
-- İlke: en az veri. Hesap/e-posta yok; her cihaz anonim oturum açar. Çocuk cihazı bir "aile" oluşturur,
-- ebeveyn telefonu 6 haneli, 10 dakika geçerli, tek kullanımlık kodla katılır.
-- Saklananlar: çocuğun takma adı/avatarı/sınıfı, günlük-haftalık özet sayılar, koruma durumu, ebeveyn komutları.
-- Saklanmayanlar: gerçek ad, konum, kişi listesi, ekran içeriği, tek tek soru cevapları.

create extension if not exists pgcrypto;

-- ---------- tablolar ----------
create table if not exists public.families (
  id uuid primary key default gen_random_uuid(),
  created_at timestamptz not null default now(),
  created_by uuid not null default auth.uid(),
  pairing_code text unique,
  pairing_expires_at timestamptz
);

create table if not exists public.family_members (
  family_id uuid not null references public.families(id) on delete cascade,
  user_id uuid not null,
  role text not null check (role in ('child_device', 'parent')),
  device_label text check (char_length(device_label) <= 40),
  platform text check (platform in ('ios', 'android', 'web')),
  created_at timestamptz not null default now(),
  last_seen_at timestamptz not null default now(),
  primary key (family_id, user_id)
);
create index if not exists family_members_user on public.family_members(user_id);

-- Çocuk cihazının yüklediği özet (çocuk başına tek satır, üzerine yazılır)
create table if not exists public.child_snapshots (
  family_id uuid not null references public.families(id) on delete cascade,
  child_key text not null check (char_length(child_key) <= 64),
  nickname text not null check (char_length(nickname) <= 30),
  avatar text check (char_length(avatar) <= 16),
  grade text check (char_length(grade) <= 16),
  state text check (char_length(state) <= 32),
  available_ms bigint not null default 0,
  pending_ms bigint not null default 0,
  session jsonb,           -- {app, remainingMs, endsAt} ödül sürüyorsa
  today jsonb not null default '{}'::jsonb,   -- {solved, correct, earnedMs, usedMs}
  week jsonb not null default '[]'::jsonb,    -- son 7 gün [{day, solved, correct, usedMs}]
  subjects jsonb not null default '[]'::jsonb,-- [{subject, solved, accuracy}]
  weak jsonb not null default '[]'::jsonb,    -- en çok zorlanılan 3 beceri/kazanım [{label, accuracy}]
  updated_at timestamptz not null default now(),
  primary key (family_id, child_key),
  check (pg_column_size(today) + pg_column_size(week) + pg_column_size(subjects) + pg_column_size(weak) < 16000)
);

-- Cihaz durumu (koruma açık mı, izin kapatıldı mı) — aile başına tek satır
create table if not exists public.device_status (
  family_id uuid primary key references public.families(id) on delete cascade,
  protection_on boolean not null default false,
  control_ready boolean not null default false,
  paused_until timestamptz,
  tamper_at timestamptz,          -- koruma izni en son ne zaman kapatıldı (Android erişilebilirlik)
  app_version text check (char_length(app_version) <= 20),
  updated_at timestamptz not null default now()
);

-- Ebeveyn komutları (ebeveyn telefonu yazar, çocuk cihazı uygular)
create table if not exists public.commands (
  id uuid primary key default gen_random_uuid(),
  family_id uuid not null references public.families(id) on delete cascade,
  child_key text check (char_length(child_key) <= 64),
  type text not null check (type in ('extra_time', 'end_reward', 'pause', 'resume', 'lock_now', 'set_daily_limit')),
  payload jsonb not null default '{}'::jsonb check (pg_column_size(payload) < 2000),
  created_by uuid not null default auth.uid(),
  created_at timestamptz not null default now(),
  consumed_at timestamptz,
  result text check (char_length(result) <= 200)
);
create index if not exists commands_pending on public.commands(family_id) where consumed_at is null;

-- ---------- yardımcılar ----------
create or replace function public.member_role(fid uuid) returns text
language sql stable security definer set search_path = public as $$
  select role from public.family_members where family_id = fid and user_id = auth.uid()
$$;

-- ---------- RLS ----------
alter table public.families enable row level security;
alter table public.family_members enable row level security;
alter table public.child_snapshots enable row level security;
alter table public.device_status enable row level security;
alter table public.commands enable row level security;

drop policy if exists fam_select on public.families;
create policy fam_select on public.families for select using (public.member_role(id) is not null);

drop policy if exists mem_select on public.family_members;
create policy mem_select on public.family_members for select using (public.member_role(family_id) is not null);
drop policy if exists mem_delete_self on public.family_members;
-- Ebeveyn telefonu ayrılabilir; çocuk cihazı aileyi silerek (unpair) ayrılır
create policy mem_delete_self on public.family_members for delete using (user_id = auth.uid() or public.member_role(family_id) = 'child_device');

drop policy if exists snap_select on public.child_snapshots;
create policy snap_select on public.child_snapshots for select using (public.member_role(family_id) is not null);
drop policy if exists snap_write on public.child_snapshots;
create policy snap_write on public.child_snapshots for all
  using (public.member_role(family_id) = 'child_device') with check (public.member_role(family_id) = 'child_device');

drop policy if exists dev_select on public.device_status;
create policy dev_select on public.device_status for select using (public.member_role(family_id) is not null);
drop policy if exists dev_write on public.device_status;
create policy dev_write on public.device_status for all
  using (public.member_role(family_id) = 'child_device') with check (public.member_role(family_id) = 'child_device');

drop policy if exists cmd_select on public.commands;
create policy cmd_select on public.commands for select using (public.member_role(family_id) is not null);
drop policy if exists cmd_insert on public.commands;
create policy cmd_insert on public.commands for insert with check (public.member_role(family_id) = 'parent' and created_by = auth.uid());
drop policy if exists cmd_consume on public.commands;
create policy cmd_consume on public.commands for update
  using (public.member_role(family_id) = 'child_device') with check (public.member_role(family_id) = 'child_device');

-- ---------- RPC'ler ----------
-- Çocuk cihazı: aile oluştur (yoksa) ve yeni eşleştirme kodu üret
create or replace function public.create_pairing(p_platform text, p_label text)
returns table (family_id uuid, code text, expires_at timestamptz)
language plpgsql security definer set search_path = public as $$
declare fid uuid; c text; tries int := 0;
begin
  if auth.uid() is null then raise exception 'oturum yok'; end if;
  select m.family_id into fid from public.family_members m where m.user_id = auth.uid() and m.role = 'child_device' limit 1;
  if fid is null then
    insert into public.families default values returning id into fid;
    insert into public.family_members(family_id, user_id, role, platform, device_label)
      values (fid, auth.uid(), 'child_device', p_platform, left(p_label, 40));
    insert into public.device_status(family_id) values (fid);
  end if;
  loop
    c := lpad((floor(random() * 1000000))::int::text, 6, '0');
    begin
      update public.families set pairing_code = c, pairing_expires_at = now() + interval '10 minutes' where id = fid;
      exit;
    exception when unique_violation then
      tries := tries + 1;
      if tries > 20 then raise exception 'kod üretilemedi'; end if;
    end;
  end loop;
  return query select fid, c, now() + interval '10 minutes';
end $$;

-- Ebeveyn telefonu: kodla katıl (kod tek kullanımlık). Kaba kuvvete karşı kullanıcı başına deneme sınırı.
create table if not exists public.pairing_attempts (
  user_id uuid not null,
  at timestamptz not null default now()
);
alter table public.pairing_attempts enable row level security;

create or replace function public.join_family(p_code text, p_platform text, p_label text)
returns uuid
language plpgsql security definer set search_path = public as $$
declare fid uuid; n int;
begin
  if auth.uid() is null then raise exception 'oturum yok'; end if;
  select count(*) into n from public.pairing_attempts where user_id = auth.uid() and at > now() - interval '15 minutes';
  if n >= 8 then raise exception 'cok_fazla_deneme'; end if;
  insert into public.pairing_attempts(user_id) values (auth.uid());
  select id into fid from public.families
    where pairing_code = p_code and pairing_expires_at > now() for update;
  -- Hata fırlatılmaz: deneme kaydı işlem geri alınmadan saklansın. İstemci null'ı "kod geçersiz" diye gösterir.
  if fid is null then return null; end if;
  insert into public.family_members(family_id, user_id, role, platform, device_label)
    values (fid, auth.uid(), 'parent', p_platform, left(p_label, 40))
    on conflict (family_id, user_id) do update set role = 'parent', last_seen_at = now();
  update public.families set pairing_code = null, pairing_expires_at = null where id = fid;
  return fid;
end $$;

-- Çocuk cihazı: eşleşmeyi tamamen kaldır (tüm veriler silinir)
create or replace function public.delete_family()
returns void
language plpgsql security definer set search_path = public as $$
declare fid uuid;
begin
  select m.family_id into fid from public.family_members m where m.user_id = auth.uid() and m.role = 'child_device' limit 1;
  if fid is not null then delete from public.families where id = fid; end if;
end $$;

-- Ebeveyn telefonu: bir aileden ayrıl
create or replace function public.leave_family(p_family uuid)
returns void
language sql security definer set search_path = public as $$
  delete from public.family_members where family_id = p_family and user_id = auth.uid() and role = 'parent'
$$;

-- Görülme zamanı
create or replace function public.touch(p_family uuid)
returns void
language sql security definer set search_path = public as $$
  update public.family_members set last_seen_at = now() where family_id = p_family and user_id = auth.uid()
$$;

revoke all on function public.create_pairing(text, text) from public, anon;
revoke all on function public.join_family(text, text, text) from public, anon;
revoke all on function public.delete_family() from public, anon;
revoke all on function public.leave_family(uuid) from public, anon;
revoke all on function public.touch(uuid) from public, anon;
grant execute on function public.create_pairing(text, text) to authenticated;
grant execute on function public.join_family(text, text, text) to authenticated;
grant execute on function public.delete_family() to authenticated;
grant execute on function public.leave_family(uuid) to authenticated;
grant execute on function public.touch(uuid) to authenticated;

-- Eski komutları ve denemeleri temizle (Supabase pg_cron varsa günlük çalıştırılır)
create or replace function public.cleanup() returns void
language sql security definer set search_path = public as $$
  delete from public.commands where created_at < now() - interval '30 days';
  delete from public.pairing_attempts where at < now() - interval '1 day';
$$;
