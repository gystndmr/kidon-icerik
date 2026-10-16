-- Anlık bildirim (Expo Push): ebeveyn komutu çocuk telefonunu hemen uyandırır; koruma izni kapatılınca ebeveyne uyarı gider.
-- Bildirim içeriği kişisel veri taşımaz: çocuk telefonuna yalnızca "komut var" sinyali, ebeveyne kısa bir uyarı metni.
create extension if not exists pg_net;

alter table public.family_members add column if not exists push_token text check (push_token is null or (char_length(push_token) <= 200 and push_token like 'ExponentPushToken[%'));

-- Cihaz kendi bildirim belirtecini kaydeder (yalnızca kendi satırı)
create or replace function public.set_push_token(p_family uuid, p_token text)
returns void
language sql security definer set search_path = public as $$
  update public.family_members set push_token = nullif(p_token, ''), last_seen_at = now()
  where family_id = p_family and user_id = auth.uid()
$$;
revoke all on function public.set_push_token(uuid, text) from public, anon;
grant execute on function public.set_push_token(uuid, text) to authenticated;

create or replace function public.push_send(messages jsonb)
returns void
language plpgsql security definer set search_path = public, extensions as $$
begin
  if messages is null or jsonb_array_length(messages) = 0 then return; end if;
  perform net.http_post(
    url := 'https://exp.host/--/api/v2/push/send',
    body := messages,
    headers := jsonb_build_object('Content-Type', 'application/json', 'Accept', 'application/json')
  );
end $$;
revoke all on function public.push_send(jsonb) from public, anon, authenticated;

-- Yeni komut → çocuk telefonuna sessiz (arka planda çalışan) bildirim; "şimdi kilitle" için ayrıca görünür bildirim
create or replace function public.on_command_insert()
returns trigger
language plpgsql security definer set search_path = public as $$
declare msgs jsonb := '[]'::jsonb; t text;
begin
  for t in select push_token from public.family_members
           where family_id = new.family_id and role = 'child_device' and push_token is not null loop
    msgs := msgs || jsonb_build_array(jsonb_build_object(
      'to', t, 'data', jsonb_build_object('kidon', 'command'), '_contentAvailable', true, 'priority', 'high'));
    if new.type in ('lock_now', 'end_reward') then
      msgs := msgs || jsonb_build_array(jsonb_build_object(
        'to', t, 'title', 'KidOn',
        'body', case when new.type = 'lock_now' then 'Ebeveynin şimdi kilitledi. Görevlere dönme zamanı!' else 'Ebeveynin ödül süresini bitirdi.' end,
        'data', jsonb_build_object('kidon', 'command'), 'sound', 'default', 'priority', 'high', 'channelId', 'kidon'));
    end if;
  end loop;
  perform public.push_send(msgs);
  return new;
end $$;
drop trigger if exists commands_push on public.commands;
create trigger commands_push after insert on public.commands for each row execute function public.on_command_insert();

-- Koruma izni kapatıldı (Android erişilebilirlik) → ebeveyn telefonlarına uyarı (aynı olay için bir kez)
create or replace function public.on_device_status_update()
returns trigger
language plpgsql security definer set search_path = public as $$
declare msgs jsonb := '[]'::jsonb; t text;
begin
  if new.tamper_at is not null and (old.tamper_at is null or new.tamper_at > old.tamper_at) then
    for t in select push_token from public.family_members
             where family_id = new.family_id and role = 'parent' and push_token is not null loop
      msgs := msgs || jsonb_build_array(jsonb_build_object(
        'to', t, 'title', '⚠️ KidOn koruması kapatıldı',
        'body', 'Çocuğun telefonunda KidOn koruma izni kapatılmış; uygulamalar şu an kilitli değil.',
        'sound', 'default', 'priority', 'high', 'channelId', 'kidon'));
    end loop;
  end if;
  perform public.push_send(msgs);
  return new;
end $$;
drop trigger if exists device_status_push on public.device_status;
create trigger device_status_push after update on public.device_status for each row execute function public.on_device_status_update();
