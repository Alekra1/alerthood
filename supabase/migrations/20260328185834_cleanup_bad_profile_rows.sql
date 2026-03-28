-- Remove profiles where username was incorrectly set to an email address
DELETE FROM public.profiles WHERE username LIKE '%@%';
