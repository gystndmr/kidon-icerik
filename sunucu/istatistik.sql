-- Kendini geliştiren içerik: isimsiz soru istatistikleri ve "Bu soruda hata var" bildirimleri.
-- Kimlik yok: uygulama oturum açmadan (yalnızca yayınlanabilir anahtarla) gönderir; satırlarda cihaz, çocuk
-- veya kullanıcı bilgisi tutulmaz, yalnızca görev kimliği + sınıf + sayılar. Kötüye kullanıma karşı IP'nin
-- günlük tuzlu özeti (geri çevrilemez) yalnızca o günün sayacı için tutulur ve her gece silinir.
create extension if not exists pgcrypto with schema extensions;

create table if not exists public.question_stats (
  task_id text not null,
  grade text not null,
  content_version int not null,
  shown int not null default 0,          -- ilk deneme sayısı
  first_correct int not null default 0,  -- ilk denemede doğru
  later_correct int not null default 0,  -- sonraki denemede doğru
  wrong_answers jsonb not null default '{}'::jsonb, -- ilk denemedeki yanlış cevap → sayı
  batches int not null default 0,        -- kaç gönderimden geldi (kabaca cihaz-gün)
  updated_at timestamptz not null default now(),
  primary key (task_id, grade, content_version)
);
create table if not exists public.question_reports (
  task_id text not null,
  grade text not null,
  content_version int not null,
  reason text not null,
  count int not null default 0,
  last_at timestamptz not null default now(),
  primary key (task_id, grade, content_version, reason)
);
create table if not exists public.stat_limits (
  ip_hash text not null,
  day date not null,
  kind text not null,
  n int not null default 0,
  primary key (ip_hash, day, kind)
);
create table if not exists public.stat_salt (id int primary key check (id = 1), salt text not null);
insert into public.stat_salt (id, salt) values (1, encode(extensions.gen_random_bytes(24), 'hex')) on conflict do nothing;

alter table public.question_stats enable row level security;
alter table public.question_reports enable row level security;
alter table public.stat_limits enable row level security;
alter table public.stat_salt enable row level security;
revoke all on public.question_stats, public.question_reports, public.stat_limits, public.stat_salt from anon, authenticated;

-- Günlük sınır (IP başına). Aşılırsa false.
create or replace function public.stat_allow(p_kind text, p_max int)
returns boolean
language plpgsql security definer set search_path = public, extensions as $$
declare
  hdr json := nullif(current_setting('request.headers', true), '')::json;
  ip text := coalesce(hdr->>'cf-connecting-ip', split_part(coalesce(hdr->>'x-forwarded-for', ''), ',', 1), 'yok');
  h text;
  cnt int;
begin
  select encode(extensions.digest(s.salt || current_date::text || trim(ip), 'sha256'), 'hex') into h from public.stat_salt s where id = 1;
  insert into public.stat_limits (ip_hash, day, kind, n) values (h, current_date, p_kind, 1)
  on conflict (ip_hash, day, kind) do update set n = stat_limits.n + 1
  returning n into cnt;
  return cnt <= p_max;
end $$;
revoke all on function public.stat_allow(text, int) from public, anon, authenticated;

-- items: [{"t":görev,"g":sınıf,"v":sürüm,"n":ilk deneme,"c":ilk denemede doğru,"l":sonra doğru,"w":{"cevap":sayı}}]
create or replace function public.submit_question_stats(items jsonb)
returns int
language plpgsql security definer set search_path = public as $$
declare
  it jsonb; n int; c int; l int; w jsonb; wk text; wv int; cleanw jsonb; done int := 0;
begin
  if items is null or jsonb_typeof(items) <> 'array' or jsonb_array_length(items) = 0 then return 0; end if;
  if jsonb_array_length(items) > 400 then raise exception 'too_many'; end if;
  if not public.stat_allow('stats', 300) then return 0; end if;
  for it in select * from jsonb_array_elements(items) loop
    if jsonb_typeof(it) <> 'object'
       or coalesce(it->>'t', '') !~ '^[A-Za-z0-9_.:-]{1,80}$'
       or coalesce(it->>'g', '') not in ('okul_oncesi','1','2','3','4','5','6','7','8')
       or coalesce(it->>'v', '') !~ '^[0-9]{1,6}$' then continue; end if;
    n := least(greatest(coalesce((it->>'n')::int, 0), 0), 30);
    c := least(greatest(coalesce((it->>'c')::int, 0), 0), n);
    l := least(greatest(coalesce((it->>'l')::int, 0), 0), 30);
    if n = 0 and l = 0 then continue; end if;
    cleanw := '{}'::jsonb;
    w := it->'w';
    if w is not null and jsonb_typeof(w) = 'object' then
      for wk, wv in select key, least(greatest(coalesce((value #>> '{}')::int, 0), 0), 30) from jsonb_each(w) limit 3 loop
        if char_length(wk) between 1 and 40 and wv > 0 then cleanw := cleanw || jsonb_build_object(wk, wv); end if;
      end loop;
    end if;
    insert into public.question_stats as q (task_id, grade, content_version, shown, first_correct, later_correct, wrong_answers, batches)
    values (it->>'t', it->>'g', (it->>'v')::int, n, c, l, cleanw, 1)
    on conflict (task_id, grade, content_version) do update set
      shown = q.shown + excluded.shown,
      first_correct = q.first_correct + excluded.first_correct,
      later_correct = q.later_correct + excluded.later_correct,
      wrong_answers = (
        select coalesce(jsonb_object_agg(k, s), '{}'::jsonb) from (
          select k, sum(v)::int s from (
            select key k, (value #>> '{}')::int v from jsonb_each(q.wrong_answers)
            union all select key, (value #>> '{}')::int from jsonb_each(excluded.wrong_answers)
          ) z group by k order by s desc limit 8
        ) y),
      batches = q.batches + 1,
      updated_at = now();
    done := done + 1;
  end loop;
  return done;
end $$;
revoke all on function public.submit_question_stats(jsonb) from public;
grant execute on function public.submit_question_stats(jsonb) to anon, authenticated;

create or replace function public.report_question(p_task text, p_grade text, p_version int, p_reason text)
returns boolean
language plpgsql security definer set search_path = public as $$
begin
  if coalesce(p_task, '') !~ '^[A-Za-z0-9_.:-]{1,80}$'
     or coalesce(p_grade, '') not in ('okul_oncesi','1','2','3','4','5','6','7','8')
     or p_version is null or p_version < 1 or p_version > 999999
     or coalesce(p_reason, '') not in ('cevap_yanlis','anlasilmiyor','yazim','uygunsuz','diger') then
    return false;
  end if;
  if not public.stat_allow('report', 60) then return false; end if;
  insert into public.question_reports as r (task_id, grade, content_version, reason, count)
  values (p_task, p_grade, p_version, p_reason, 1)
  on conflict (task_id, grade, content_version, reason) do update set count = r.count + 1, last_at = now();
  return true;
end $$;
revoke all on function public.report_question(text, text, int, text) from public;
grant execute on function public.report_question(text, text, int, text) to anon, authenticated;

-- Haftalık içerik görevi için toplu okuma (yalnız sayılar; kişisel veri yok)
create or replace function public.question_quality()
returns jsonb
language sql stable security definer set search_path = public as $$
  select jsonb_build_object(
    'generated_at', now(),
    'stats', coalesce((select jsonb_agg(jsonb_build_object(
        't', task_id, 'g', grade, 'v', content_version, 'n', shown, 'c', first_correct, 'l', later_correct,
        'w', wrong_answers, 'b', batches) order by task_id, grade, content_version)
      from public.question_stats), '[]'::jsonb),
    'reports', coalesce((select jsonb_agg(jsonb_build_object(
        't', task_id, 'g', grade, 'v', content_version, 'r', reason, 'n', count, 'at', last_at) order by task_id)
      from public.question_reports), '[]'::jsonb))
$$;
revoke all on function public.question_quality() from public;
grant execute on function public.question_quality() to anon, authenticated;

create or replace function public.stats_cleanup()
returns void language sql security definer set search_path = public as $$
  delete from public.stat_limits where day < current_date;
$$;
revoke all on function public.stats_cleanup() from public, anon, authenticated;
select cron.unschedule('kidon-stats-cleanup') where exists (select 1 from cron.job where jobname = 'kidon-stats-cleanup');
select cron.schedule('kidon-stats-cleanup', '23 3 * * *', 'select public.stats_cleanup()');
