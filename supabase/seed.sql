-- Seed data: 38 global areas + 50 Chicago events for demo

-- === GLOBAL AREAS ===

insert into public.areas (name, city, slug, center, radius_km) values
-- Chicago (from design mockups)
('West Loop', 'Chicago', 'chicago-west-loop', extensions.st_setsrid(extensions.st_makepoint(-87.6553, 41.8827), 4326), 2.5),
('River North', 'Chicago', 'chicago-river-north', extensions.st_setsrid(extensions.st_makepoint(-87.6315, 41.8920), 4326), 2.0),
-- North America
('Manhattan', 'New York', 'nyc-manhattan', extensions.st_setsrid(extensions.st_makepoint(-73.9712, 40.7831), 4326), 5.0),
('Brooklyn', 'New York', 'nyc-brooklyn', extensions.st_setsrid(extensions.st_makepoint(-73.9442, 40.6782), 4326), 5.0),
('Downtown LA', 'Los Angeles', 'la-downtown', extensions.st_setsrid(extensions.st_makepoint(-118.2437, 34.0522), 4326), 5.0),
('South Central', 'Los Angeles', 'la-south-central', extensions.st_setsrid(extensions.st_makepoint(-118.2815, 33.9425), 4326), 5.0),
('San Francisco', 'San Francisco', 'sf-downtown', extensions.st_setsrid(extensions.st_makepoint(-122.4194, 37.7749), 4326), 4.0),
('Miami Beach', 'Miami', 'miami-beach', extensions.st_setsrid(extensions.st_makepoint(-80.1300, 25.7907), 4326), 4.0),
('Houston Downtown', 'Houston', 'houston-downtown', extensions.st_setsrid(extensions.st_makepoint(-95.3698, 29.7604), 4326), 5.0),
('Washington DC', 'Washington', 'dc-downtown', extensions.st_setsrid(extensions.st_makepoint(-77.0369, 38.9072), 4326), 5.0),
('Toronto Downtown', 'Toronto', 'toronto-downtown', extensions.st_setsrid(extensions.st_makepoint(-79.3832, 43.6532), 4326), 5.0),
('Mexico City Centro', 'Mexico City', 'cdmx-centro', extensions.st_setsrid(extensions.st_makepoint(-99.1332, 19.4326), 4326), 5.0),
-- Europe
('Central London', 'London', 'london-central', extensions.st_setsrid(extensions.st_makepoint(-0.1276, 51.5074), 4326), 5.0),
('Paris Centre', 'Paris', 'paris-centre', extensions.st_setsrid(extensions.st_makepoint(2.3522, 48.8566), 4326), 4.0),
('Berlin Mitte', 'Berlin', 'berlin-mitte', extensions.st_setsrid(extensions.st_makepoint(13.4050, 52.5200), 4326), 5.0),
('Madrid Centro', 'Madrid', 'madrid-centro', extensions.st_setsrid(extensions.st_makepoint(-3.7038, 40.4168), 4326), 4.0),
('Rome Centro', 'Rome', 'rome-centro', extensions.st_setsrid(extensions.st_makepoint(12.4964, 41.9028), 4326), 4.0),
('Kyiv Center', 'Kyiv', 'kyiv-center', extensions.st_setsrid(extensions.st_makepoint(30.5234, 50.4501), 4326), 8.0),
('Istanbul Center', 'Istanbul', 'istanbul-center', extensions.st_setsrid(extensions.st_makepoint(28.9784, 41.0082), 4326), 6.0),
('Moscow Center', 'Moscow', 'moscow-center', extensions.st_setsrid(extensions.st_makepoint(37.6173, 55.7558), 4326), 6.0),
-- Middle East & Africa
('Tel Aviv', 'Tel Aviv', 'tel-aviv', extensions.st_setsrid(extensions.st_makepoint(34.7818, 32.0853), 4326), 5.0),
('Baghdad Center', 'Baghdad', 'baghdad-center', extensions.st_setsrid(extensions.st_makepoint(44.3661, 33.3152), 4326), 8.0),
('Cairo Center', 'Cairo', 'cairo-center', extensions.st_setsrid(extensions.st_makepoint(31.2357, 30.0444), 4326), 6.0),
('Lagos Island', 'Lagos', 'lagos-island', extensions.st_setsrid(extensions.st_makepoint(3.3792, 6.5244), 4326), 6.0),
('Johannesburg CBD', 'Johannesburg', 'joburg-cbd', extensions.st_setsrid(extensions.st_makepoint(28.0473, -26.2041), 4326), 5.0),
('Nairobi Center', 'Nairobi', 'nairobi-center', extensions.st_setsrid(extensions.st_makepoint(36.8219, -1.2921), 4326), 5.0),
-- Asia
('Tokyo Shinjuku', 'Tokyo', 'tokyo-shinjuku', extensions.st_setsrid(extensions.st_makepoint(139.6917, 35.6895), 4326), 5.0),
('Mumbai South', 'Mumbai', 'mumbai-south', extensions.st_setsrid(extensions.st_makepoint(72.8777, 19.0760), 4326), 5.0),
('Beijing Chaoyang', 'Beijing', 'beijing-chaoyang', extensions.st_setsrid(extensions.st_makepoint(116.4074, 39.9042), 4326), 6.0),
('Shanghai Pudong', 'Shanghai', 'shanghai-pudong', extensions.st_setsrid(extensions.st_makepoint(121.4737, 31.2304), 4326), 6.0),
('Manila Metro', 'Manila', 'manila-metro', extensions.st_setsrid(extensions.st_makepoint(120.9842, 14.5995), 4326), 5.0),
('Bangkok Center', 'Bangkok', 'bangkok-center', extensions.st_setsrid(extensions.st_makepoint(100.5018, 13.7563), 4326), 5.0),
('Singapore Central', 'Singapore', 'singapore-central', extensions.st_setsrid(extensions.st_makepoint(103.8198, 1.3521), 4326), 5.0),
('Kabul Center', 'Kabul', 'kabul-center', extensions.st_setsrid(extensions.st_makepoint(69.1723, 34.5553), 4326), 8.0),
-- South America
('São Paulo Centro', 'São Paulo', 'saopaulo-centro', extensions.st_setsrid(extensions.st_makepoint(-46.6333, -23.5505), 4326), 5.0),
('Buenos Aires Centro', 'Buenos Aires', 'buenosaires-centro', extensions.st_setsrid(extensions.st_makepoint(-58.3816, -34.6037), 4326), 5.0),
('Bogotá Centro', 'Bogotá', 'bogota-centro', extensions.st_setsrid(extensions.st_makepoint(-74.0721, 4.7110), 4326), 5.0),
-- Oceania
('Sydney CBD', 'Sydney', 'sydney-cbd', extensions.st_setsrid(extensions.st_makepoint(151.2093, -33.8688), 4326), 4.0);

-- === CHICAGO DEMO EVENTS (50) ===

do $$
declare
  west_loop_id uuid;
  river_north_id uuid;
begin
  select id into west_loop_id from public.areas where slug = 'chicago-west-loop';
  select id into river_north_id from public.areas where slug = 'chicago-river-north';

  -- West Loop (25 events)
  insert into public.events (area_id, title, description, threat_type, severity, occurred_at, location, location_label, source_type) values
  (west_loop_id, 'Armed robbery at Randolph St', 'Two suspects fled on foot after robbing a pedestrian at gunpoint', 'crime', 'critical', now() - interval '2 hours', extensions.st_setsrid(extensions.st_makepoint(-87.6548, 41.8841), 4326), 'Randolph St & Halsted', 'news'),
  (west_loop_id, 'Vehicle break-in cluster reported', 'Multiple vehicles broken into overnight in parking garage', 'crime', 'medium', now() - interval '8 hours', extensions.st_setsrid(extensions.st_makepoint(-87.6590, 41.8815), 4326), 'W Monroe St', 'news'),
  (west_loop_id, 'Shoplifting incident at grocery store', 'Suspect apprehended by security after stealing merchandise', 'crime', 'low', now() - interval '1 day', extensions.st_setsrid(extensions.st_makepoint(-87.6520, 41.8850), 4326), 'W Madison St & Morgan', 'news'),
  (west_loop_id, 'Assault near transit station', 'Victim transported to hospital with minor injuries', 'crime', 'high', now() - interval '5 hours', extensions.st_setsrid(extensions.st_makepoint(-87.6568, 41.8862), 4326), 'Morgan CTA Station', 'news'),
  (west_loop_id, 'Carjacking attempt thwarted', 'Driver escaped after suspect approached with weapon', 'crime', 'high', now() - interval '3 days', extensions.st_setsrid(extensions.st_makepoint(-87.6610, 41.8790), 4326), 'W Adams & Racine', 'news'),
  (west_loop_id, 'Package theft from building lobby', 'Multiple packages stolen from residential building', 'crime', 'low', now() - interval '2 days', extensions.st_setsrid(extensions.st_makepoint(-87.6530, 41.8835), 4326), 'W Washington Blvd', 'news'),
  (west_loop_id, 'Water main break on Lake St', 'City crews responding to major water main break causing flooding', 'infrastructure', 'high', now() - interval '4 hours', extensions.st_setsrid(extensions.st_makepoint(-87.6575, 41.8856), 4326), 'W Lake St & Green St', 'news'),
  (west_loop_id, 'Power outage affecting 3 blocks', 'ComEd reports outage affecting ~500 customers', 'infrastructure', 'medium', now() - interval '6 hours', extensions.st_setsrid(extensions.st_makepoint(-87.6540, 41.8820), 4326), 'W Jackson Blvd area', 'news'),
  (west_loop_id, 'Gas leak reported on Fulton Market', 'Peoples Gas investigating reports of gas smell', 'infrastructure', 'critical', now() - interval '1 hour', extensions.st_setsrid(extensions.st_makepoint(-87.6560, 41.8868), 4326), 'Fulton Market District', 'news'),
  (west_loop_id, 'Road closure for emergency repairs', 'Sinkhole developing on Peoria St requires lane closure', 'infrastructure', 'medium', now() - interval '12 hours', extensions.st_setsrid(extensions.st_makepoint(-87.6497, 41.8830), 4326), 'S Peoria St', 'news'),
  (west_loop_id, 'Large protest march on Madison', 'Organized protest moving eastbound, expect traffic delays', 'disturbance', 'medium', now() - interval '3 hours', extensions.st_setsrid(extensions.st_makepoint(-87.6555, 41.8818), 4326), 'W Madison St', 'news'),
  (west_loop_id, 'Noise complaint: construction 11pm', 'After-hours construction work causing noise disturbance', 'disturbance', 'low', now() - interval '14 hours', extensions.st_setsrid(extensions.st_makepoint(-87.6580, 41.8845), 4326), 'W Randolph & Peoria', 'news'),
  (west_loop_id, 'Bar fight spills onto street', 'Altercation between patrons outside nightlife venue', 'disturbance', 'medium', now() - interval '16 hours', extensions.st_setsrid(extensions.st_makepoint(-87.6515, 41.8855), 4326), 'Randolph St bar district', 'news'),
  (west_loop_id, 'Flash flood warning issued', 'Low-lying areas at risk from heavy rainfall', 'natural', 'high', now() - interval '30 minutes', extensions.st_setsrid(extensions.st_makepoint(-87.6565, 41.8810), 4326), 'West Loop lowlands', 'news'),
  (west_loop_id, 'Tree down blocking sidewalk', 'Large tree fell due to high winds, crews en route', 'natural', 'low', now() - interval '1 day', extensions.st_setsrid(extensions.st_makepoint(-87.6600, 41.8860), 4326), 'W Fulton St', 'news'),
  (west_loop_id, 'Morning mugging near CTA', 'Victim robbed at 7am during commute', 'crime', 'high', now() - interval '2 days' + interval '7 hours', extensions.st_setsrid(extensions.st_makepoint(-87.6535, 41.8870), 4326), 'Clinton CTA Blue Line', 'news'),
  (west_loop_id, 'Late night assault', 'Incident occurred at 1am outside club', 'crime', 'high', now() - interval '4 days' + interval '1 hour', extensions.st_setsrid(extensions.st_makepoint(-87.6550, 41.8840), 4326), 'W Randolph entertainment district', 'news'),
  (west_loop_id, 'Afternoon break-in at office', 'Commercial burglary reported at 2pm', 'crime', 'medium', now() - interval '5 days' + interval '14 hours', extensions.st_setsrid(extensions.st_makepoint(-87.6585, 41.8825), 4326), 'W Monroe St offices', 'news'),
  (west_loop_id, 'Evening street harassment', 'Multiple reports of aggressive panhandling at 8pm', 'disturbance', 'low', now() - interval '3 days' + interval '20 hours', extensions.st_setsrid(extensions.st_makepoint(-87.6545, 41.8852), 4326), 'W Madison & Halsted', 'news'),
  (west_loop_id, 'Catalytic converter theft ring', 'Police investigating series of thefts in parking lots', 'crime', 'medium', now() - interval '6 days', extensions.st_setsrid(extensions.st_makepoint(-87.6595, 41.8800), 4326), 'W Van Buren parking', 'news'),
  (west_loop_id, 'Graffiti vandalism spree', 'Multiple buildings tagged overnight', 'disturbance', 'low', now() - interval '5 days', extensions.st_setsrid(extensions.st_makepoint(-87.6510, 41.8865), 4326), 'Green St corridor', 'news'),
  (west_loop_id, 'Suspicious package at transit', 'Area cleared, package was abandoned luggage', 'crime', 'medium', now() - interval '4 days', extensions.st_setsrid(extensions.st_makepoint(-87.6570, 41.8858), 4326), 'UIC-Halsted station', 'news'),
  (west_loop_id, 'Burst pipe causes building evacuation', 'Tenants displaced while repairs underway', 'infrastructure', 'medium', now() - interval '7 days', extensions.st_setsrid(extensions.st_makepoint(-87.6525, 41.8842), 4326), 'W Washington lofts', 'news'),
  (west_loop_id, 'Ice storm damage to powerlines', 'Several streets without power after storm', 'natural', 'high', now() - interval '10 days', extensions.st_setsrid(extensions.st_makepoint(-87.6560, 41.8808), 4326), 'W Harrison & Halsted', 'news'),
  (west_loop_id, 'DUI crash into storefront', 'Driver arrested after crashing into restaurant', 'crime', 'high', now() - interval '6 days', extensions.st_setsrid(extensions.st_makepoint(-87.6542, 41.8875), 4326), 'Fulton Market restaurant row', 'news');

  -- River North (25 events)
  insert into public.events (area_id, title, description, threat_type, severity, occurred_at, location, location_label, source_type) values
  (river_north_id, 'Shooting near Magnificent Mile', 'One injured in shooting, suspect at large', 'crime', 'critical', now() - interval '1 hour', extensions.st_setsrid(extensions.st_makepoint(-87.6244, 41.8932), 4326), 'N Michigan Ave & Ohio', 'news'),
  (river_north_id, 'Tourist pickpocketed on State St', 'Wallet stolen in crowded retail area', 'crime', 'low', now() - interval '5 hours', extensions.st_setsrid(extensions.st_makepoint(-87.6278, 41.8918), 4326), 'N State St shopping', 'news'),
  (river_north_id, 'Road rage incident on LaSalle', 'Driver brandished weapon during traffic dispute', 'crime', 'high', now() - interval '3 hours', extensions.st_setsrid(extensions.st_makepoint(-87.6325, 41.8945), 4326), 'N LaSalle Dr', 'news'),
  (river_north_id, 'Attempted ATM robbery', 'Suspect fled when alarm triggered', 'crime', 'high', now() - interval '10 hours', extensions.st_setsrid(extensions.st_makepoint(-87.6290, 41.8905), 4326), 'W Grand Ave', 'news'),
  (river_north_id, 'Retail theft at luxury store', 'Organized group grabbed merchandise and fled', 'crime', 'medium', now() - interval '1 day', extensions.st_setsrid(extensions.st_makepoint(-87.6255, 41.8940), 4326), 'N Rush St boutiques', 'news'),
  (river_north_id, 'Phone snatching on bridge', 'Thief grabbed phone from pedestrian on Wells St bridge', 'crime', 'medium', now() - interval '2 days', extensions.st_setsrid(extensions.st_makepoint(-87.6340, 41.8888), 4326), 'Wells St Bridge', 'news'),
  (river_north_id, 'CTA elevator out of service', 'Grand station elevator down, use stairs or alternate route', 'infrastructure', 'low', now() - interval '2 hours', extensions.st_setsrid(extensions.st_makepoint(-87.6285, 41.8914), 4326), 'Grand CTA Red Line', 'news'),
  (river_north_id, 'Traffic signal malfunction', 'Intersection signals cycling incorrectly', 'infrastructure', 'medium', now() - interval '4 hours', extensions.st_setsrid(extensions.st_makepoint(-87.6310, 41.8925), 4326), 'Clark & Ontario', 'news'),
  (river_north_id, 'Building facade falling debris', 'Sidewalk closed after bricks fell from aging building', 'infrastructure', 'high', now() - interval '6 hours', extensions.st_setsrid(extensions.st_makepoint(-87.6265, 41.8950), 4326), 'N Dearborn St', 'news'),
  (river_north_id, 'Street flooding from storm drain', 'Backed up drain causing localized flooding', 'infrastructure', 'medium', now() - interval '8 hours', extensions.st_setsrid(extensions.st_makepoint(-87.6335, 41.8900), 4326), 'W Hubbard & Wells', 'news'),
  (river_north_id, 'Nightclub brawl', 'Large fight broke out at River North venue, 3 arrested', 'disturbance', 'high', now() - interval '14 hours', extensions.st_setsrid(extensions.st_makepoint(-87.6300, 41.8935), 4326), 'W Erie nightlife strip', 'news'),
  (river_north_id, 'Street racing on Wacker Dr', 'Multiple vehicles doing donuts, blocking traffic', 'disturbance', 'medium', now() - interval '16 hours', extensions.st_setsrid(extensions.st_makepoint(-87.6355, 41.8885), 4326), 'Lower Wacker Dr', 'news'),
  (river_north_id, 'Aggressive street vendor confrontation', 'Argument escalated between vendors and pedestrians', 'disturbance', 'low', now() - interval '1 day', extensions.st_setsrid(extensions.st_makepoint(-87.6250, 41.8928), 4326), 'N Michigan Ave', 'news'),
  (river_north_id, 'Fireworks set off in park', 'Unauthorized fireworks causing complaints', 'disturbance', 'low', now() - interval '2 days', extensions.st_setsrid(extensions.st_makepoint(-87.6270, 41.8960), 4326), 'Milton Lee Olive Park', 'news'),
  (river_north_id, 'High wind warning for lakefront', 'Gusts up to 55mph expected, secure loose items', 'natural', 'medium', now() - interval '45 minutes', extensions.st_setsrid(extensions.st_makepoint(-87.6220, 41.8955), 4326), 'Lakefront Trail north', 'news'),
  (river_north_id, 'River level rising rapidly', 'Chicago River approaching flood stage in the area', 'natural', 'high', now() - interval '2 hours', extensions.st_setsrid(extensions.st_makepoint(-87.6360, 41.8890), 4326), 'Chicago River & Wells', 'news'),
  (river_north_id, 'Morning jogger mugged at 6am', 'Runner assaulted near lakefront path', 'crime', 'high', now() - interval '3 days' + interval '6 hours', extensions.st_setsrid(extensions.st_makepoint(-87.6230, 41.8948), 4326), 'Lakefront Trail', 'news'),
  (river_north_id, 'Lunchtime phone snatch', 'Theft of phone from outdoor diner at noon', 'crime', 'medium', now() - interval '4 days' + interval '12 hours', extensions.st_setsrid(extensions.st_makepoint(-87.6295, 41.8920), 4326), 'W Illinois St restaurants', 'news'),
  (river_north_id, 'Evening harassment on subway platform', 'Verbal harassment reported at 9pm', 'disturbance', 'medium', now() - interval '5 days' + interval '21 hours', extensions.st_setsrid(extensions.st_makepoint(-87.6280, 41.8910), 4326), 'Chicago CTA Red Line', 'news'),
  (river_north_id, 'Late night car window smashing', 'Series of car break-ins between 2-4am', 'crime', 'medium', now() - interval '3 days' + interval '3 hours', extensions.st_setsrid(extensions.st_makepoint(-87.6320, 41.8930), 4326), 'N Clark St parking', 'news'),
  (river_north_id, 'Purse snatching outside hotel', 'Tourist targeted outside hotel entrance', 'crime', 'medium', now() - interval '6 days', extensions.st_setsrid(extensions.st_makepoint(-87.6260, 41.8942), 4326), 'N Rush St hotel district', 'news'),
  (river_north_id, 'Basement flooding in condos', 'Heavy rain overwhelmed drainage in older buildings', 'natural', 'medium', now() - interval '8 days', extensions.st_setsrid(extensions.st_makepoint(-87.6305, 41.8915), 4326), 'W Huron residential', 'news'),
  (river_north_id, 'Scaffolding collapse scare', 'Partial scaffolding dislodged in high winds, no injuries', 'infrastructure', 'high', now() - interval '5 days', extensions.st_setsrid(extensions.st_makepoint(-87.6275, 41.8952), 4326), 'N State & Division', 'news'),
  (river_north_id, 'Drug dealing hotspot crackdown', 'Police operation targeting known dealing area', 'crime', 'medium', now() - interval '7 days', extensions.st_setsrid(extensions.st_makepoint(-87.6345, 41.8895), 4326), 'Kinzie St underpass', 'news'),
  (river_north_id, 'Smoke from restaurant kitchen fire', 'Minor fire contained, building evacuated as precaution', 'infrastructure', 'medium', now() - interval '9 days', extensions.st_setsrid(extensions.st_makepoint(-87.6315, 41.8938), 4326), 'W Erie St restaurants', 'news');

end $$;
