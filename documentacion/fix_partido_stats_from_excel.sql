-- fix_partido_stats_from_excel.sql
-- Updates minuto_primer_gol (42+2 partidos) and decisiones_var (5 partidos)
-- Generated from db030c2d-20260623check.xlsx

BEGIN;

-- decisiones_var fixes (5 partidos)
UPDATE partido SET decisiones_var = 2 WHERE id = 146;
UPDATE partido SET decisiones_var = 0 WHERE id = 150;
UPDATE partido SET decisiones_var = 0 WHERE id = 148;
UPDATE partido SET decisiones_var = 2 WHERE id = 169;
UPDATE partido SET decisiones_var = 1 WHERE id = 180;

-- minuto_primer_gol updates (44 partidos, NULL = no goal / 0-0)
UPDATE partido SET minuto_primer_gol = 10 WHERE id = 143;
UPDATE partido SET minuto_primer_gol = 59 WHERE id = 144;
UPDATE partido SET minuto_primer_gol = 21 WHERE id = 145;
UPDATE partido SET minuto_primer_gol = 7 WHERE id = 146;
UPDATE partido SET minuto_primer_gol = 28 WHERE id = 149;
UPDATE partido SET minuto_primer_gol = 27 WHERE id = 150;
UPDATE partido SET minuto_primer_gol = 21 WHERE id = 148;
UPDATE partido SET minuto_primer_gol = 17 WHERE id = 147;
UPDATE partido SET minuto_primer_gol = 90 WHERE id = 153;
UPDATE partido SET minuto_primer_gol = 6 WHERE id = 151;
UPDATE partido SET minuto_primer_gol = 51 WHERE id = 152;
UPDATE partido SET minuto_primer_gol = 7 WHERE id = 154;
UPDATE partido SET minuto_primer_gol = 41 WHERE id = 157;
UPDATE partido SET minuto_primer_gol = 7 WHERE id = 158;
UPDATE partido SET minuto_primer_gol = 20 WHERE id = 156;
UPDATE partido SET minuto_primer_gol = 66 WHERE id = 159;
UPDATE partido SET minuto_primer_gol = 29 WHERE id = 160;
UPDATE partido SET minuto_primer_gol = 17 WHERE id = 161;
UPDATE partido SET minuto_primer_gol = 21 WHERE id = 162;
UPDATE partido SET minuto_primer_gol = 95 WHERE id = 165;
UPDATE partido SET minuto_primer_gol = 12 WHERE id = 164;
UPDATE partido SET minuto_primer_gol = 6 WHERE id = 163;
UPDATE partido SET minuto_primer_gol = 40 WHERE id = 166;
UPDATE partido SET minuto_primer_gol = 6 WHERE id = 167;
UPDATE partido SET minuto_primer_gol = 74 WHERE id = 168;
UPDATE partido SET minuto_primer_gol = 16 WHERE id = 169;
UPDATE partido SET minuto_primer_gol = 50 WHERE id = 170;
UPDATE partido SET minuto_primer_gol = 23 WHERE id = 173;
UPDATE partido SET minuto_primer_gol = 2 WHERE id = 172;
UPDATE partido SET minuto_primer_gol = 2 WHERE id = 174;
UPDATE partido SET minuto_primer_gol = 11 WHERE id = 171;
UPDATE partido SET minuto_primer_gol = 30 WHERE id = 176;
UPDATE partido SET minuto_primer_gol = NULL WHERE id = 177;
UPDATE partido SET minuto_primer_gol = 5 WHERE id = 175;
UPDATE partido SET minuto_primer_gol = 4 WHERE id = 178;
UPDATE partido SET minuto_primer_gol = 21 WHERE id = 181;
UPDATE partido SET minuto_primer_gol = NULL WHERE id = 180;
UPDATE partido SET minuto_primer_gol = 15 WHERE id = 182;
UPDATE partido SET minuto_primer_gol = 43 WHERE id = 185;
UPDATE partido SET minuto_primer_gol = 14 WHERE id = 184;
UPDATE partido SET minuto_primer_gol = 38 WHERE id = 183;
UPDATE partido SET minuto_primer_gol = 36 WHERE id = 186;
UPDATE partido SET minuto_primer_gol = NULL WHERE id = 155;
UPDATE partido SET minuto_primer_gol = 10 WHERE id = 179;

COMMIT;
