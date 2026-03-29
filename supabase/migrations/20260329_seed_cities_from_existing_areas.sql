-- Mark existing areas as cities and set country codes based on city names
-- This enables the boundary ingestion service to fetch neighborhoods for them

-- Set all existing areas to city type (they represent cities, not neighborhoods)
UPDATE public.areas
SET area_type = 'city'
WHERE area_type = 'neighborhood'
  AND parent_id IS NULL
  AND osm_id IS NULL;

-- Set country codes for known cities
-- UK cities
UPDATE public.areas SET country_code = 'GB'
WHERE city IN ('London', 'Manchester', 'Birmingham', 'Liverpool', 'Leeds', 'Sheffield',
               'Bristol', 'Newcastle', 'Nottingham', 'Glasgow', 'Edinburgh', 'Cardiff',
               'Leicester')
  AND country_code IS NULL;

-- German cities
UPDATE public.areas SET country_code = 'DE'
WHERE city IN ('Berlin', 'Munich', 'Hamburg', 'Frankfurt', 'Cologne', 'Stuttgart',
               'Düsseldorf', 'Dortmund', 'Essen', 'Leipzig', 'Dresden', 'Nuremberg')
  AND country_code IS NULL;

-- French cities
UPDATE public.areas SET country_code = 'FR'
WHERE city IN ('Paris', 'Lyon', 'Marseille', 'Toulouse', 'Nice', 'Nantes',
               'Strasbourg', 'Montpellier', 'Bordeaux', 'Lille', 'Rennes',
               'Grenoble')
  AND country_code IS NULL;

-- Bulgarian cities
UPDATE public.areas SET country_code = 'BG'
WHERE city IN ('Sofia', 'Plovdiv', 'Varna', 'Burgas', 'Stara Zagora', 'Ruse',
               'Pleven', 'Sliven', 'Dobrich', 'Shumen', 'Pernik', 'Haskovo',
               'Yambol', 'Pazardzhik', 'Blagoevgrad', 'Veliko Tarnovo', 'Vratsa',
               'Gabrovo', 'Vidin', 'Kazanlak', 'Kyustendil',
               'Montana', 'Dimitrovgrad', 'Targovishte', 'Lovech', 'Silistra',
               'Dupnitsa', 'Razgrad', 'Kardzhali',
               'Sandanski', 'Sevlievo', 'Lom', 'Karlovo',
               'Troyan', 'Botevgrad',
               'Panagyurishte', 'Berkovitsa',
               'Pomorie', 'Petrich', 'Smolyan',
               'Gorna Oryahovitsa', 'Bansko', 'Kavarna', 'Nessebar', 'Sozopol')
  AND country_code IS NULL;

-- Fallback: any remaining areas without country_code
UPDATE public.areas SET country_code = 'GB'
WHERE country_code IS NULL;
