# Effective Paths ingestion report

Source: `tables/effective_paths/*.xlsx`.

## Copy of Bots v2.2.xlsx
- Size: 792338 bytes
- Sheets: Home Page, IDS, _IDS, Master Sheet, Golden Bot Path, DVT_Bot, Amplify Bot Path, Thunder Bot Path, All Bots, GB Cooldowns, EXPORT

### Sheet: Home Page
- Dimensions: None rows × None cols
- First non-empty header-like row: 4
- Header values (non-empty): ['=HYPERLINK("https://docs.google.com/spreadsheets/d/1i35r-Tlfx5o1QIdtAYqgVkK2Hep9lH0PQ9Y7BtlyOBQ/copy", "Bots Initial Link")', 'Sheet Tab', 'Main Contributor', 'Helpers']
- Formula cells: 5 (scanned 319 cells)
- Top formulas (up to 10):
  - =HYPERLINK("https://docs.google.com/spreadsheets/d/1i35r-Tlfx5o1QIdtAYqgVkK2Hep9lH0PQ9Y7BtlyOBQ/copy", "Bots Initial Link") (count=1)
  - =IFERROR(__xludf.DUMMYFUNCTION("IMPORTRANGE(""1i35r-Tlfx5o1QIdtAYqgVkK2Hep9lH0PQ9Y7BtlyOBQ"", ""'Home Page'!B12:C13"")"),"v2.2") (count=1)
  - =IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),"feat: Fanta path") (count=1)
  - =IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),"v2.1.3") (count=1)
  - =IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),"fix: Flame bot range dropdown values") (count=1)
- Preview (first 5 rows × 10 cols):
  - [None, None, None, None, None, None, None, None, None, None]
  - [None, 'Bots', None, None, None, None, None, None, None, None]
  - [None, None, None, None, None, None, None, None, None, None]
  - [None, '=HYPERLINK("https://docs.google.com/spreadsheets/d/1i35r-Tlfx5o1QIdtAYqgVkK2Hep9lH0PQ9Y7BtlyOBQ/copy", "Bots Initial Link")', None, None, None, None, 'Sheet Tab', 'Main Contributor', 'Helpers', None]
  - [None, None, None, None, None, None, None, None, None, None]

### Sheet: IDS
- Dimensions: None rows × None cols
- First non-empty header-like row: 4
- Header values (non-empty): ['This Sheet ID is :', '1gopHNYu4SgI0UbRvscCV4_C1gct7FXr5GBBcjCzCxC0', '=IFERROR(__xludf.DUMMYFUNCTION("HYPERLINK(""https://script.google.com/macros/s/AKfycbyEXwcNtNkGgRiu-XO_VywN1vIHXRfwH5C8IOu8Y2dqEZXMxFEGHmTJvScB2zlr8NoAvQ/exec?newSheetID="" & $C$4 & ""&oldSheetID="" & REGEXEXTRACT(INDEX(IMPORTRANGE($D$6,""IDS!E:E""), MATCH(TRUE, ISNUMBER(SEARCH(\'Home Pa"&"ge\'!$B$2, IMPORTRANGE($D$6,""IDS!C:C""))), 0)), ""/d/([a-zA-Z0-9-_]+)"") & ""&idMasterID="" & REGEXEXTRACT($D$6, ""/d/([a-zA-Z0-9-_]+)"") & ""&sheetType="" & ENCODEURL(\'Home Page\'!$B$2), ""Import data using Web App"")"),"Import data using Web App")']
- Formula cells: 6 (scanned 268 cells)
- Top formulas (up to 10):
  - =HYPERLINK("https://workspace.google.com/marketplace/app/the_tower_import_data/1031925368251?flow_type=2", "Import data using addon (desktop only)") (count=1)
  - =IFERROR(__xludf.DUMMYFUNCTION("HYPERLINK(""https://script.google.com/macros/s/AKfycbyEXwcNtNkGgRiu-XO_VywN1vIHXRfwH5C8IOu8Y2dqEZXMxFEGHmTJvScB2zlr8NoAvQ/exec?newSheetID="" & $C$4 & ""&oldSheetID="" & REGEXEXTRACT(INDEX(IMPORTRANGE($D$6,""IDS!E:E""), MATCH(TRUE, ISNUMBER(SEARCH('Home Pa"&"ge'!$B$2, IMPORTRANGE($D$6,""IDS!C:C""))), 0)), ""/d/([a-zA-Z0-9-_]+)"") & ""&idMasterID="" & REGEXEXTRACT($D$6, ""/d/([a-zA-Z0-9-_]+)"") & ""&sheetType="" & ENCODEURL('Home Page'!$B$2), ""Import data using Web App"")"),"Import data using Web App") (count=1)
  - =IFERROR(__xludf.DUMMYFUNCTION("IFERROR(C6.url, IFS(LEFT(C6,8)=""https://"", C6, LEN(C6)=44, ""https://docs.google.com/spreadsheets/d/"" & C6 & ""/edit"", TRUE, C6))"),"https://docs.google.com/spreadsheets/d/18XbHJtHzu8tjqnP_9JcsZFA6jIwjOKRYmzBzOYBMv2I/edit") (count=1)
  - =IFERROR(__xludf.DUMMYFUNCTION("IF(D6<>"""", IF(IMPORTRANGE(D6,""EXPORT!A1"") = F6, ""✅"", ""Wrong ID or Version""), """")"),"✅") (count=1)
  - =HYPERLINK("https://docs.google.com/spreadsheets/d/1osjoqKmMwtOWs7Up3e21-3ofN1RHOjsgKV6y3dc6rgE/copy", "1️⃣ Copy Me") (count=1)
  - =IFS(
  ISERROR(E6), "3️⃣ Click on #REF! and then AUTHORISE ↗",
  E6="", "2️⃣ Please input your IDS Master's ID here ⤴️",
  E6="✅", HYPERLINK(D6, "Go to my IDS Master Sheet"),
  TRUE, "") (count=1)
- Preview (first 5 rows × 10 cols):
  - [None, None, None, None, None, None, None, None, None, None]
  - [None, 'The IDS System', None, None, None, None, None, None, '=HYPERLINK("https://workspace.google.com/marketplace/app/the_tower_import_data/1031925368251?flow_type=2", "Import data using addon (desktop only)")', None]
  - [None, None, None, None, None, None, None, None, None, None]
  - [None, 'This Sheet ID is :', '1gopHNYu4SgI0UbRvscCV4_C1gct7FXr5GBBcjCzCxC0', None, None, None, None, None, '=IFERROR(__xludf.DUMMYFUNCTION("HYPERLINK(""https://script.google.com/macros/s/AKfycbyEXwcNtNkGgRiu-XO_VywN1vIHXRfwH5C8IOu8Y2dqEZXMxFEGHmTJvScB2zlr8NoAvQ/exec?newSheetID="" & $C$4 & ""&oldSheetID="" & REGEXEXTRACT(INDEX(IMPORTRANGE($D$6,""IDS!E:E""), MATCH(TRUE, ISNUMBER(SEARCH(\'Home Pa"&"ge\'!$B$2, IMPORTRANGE($D$6,""IDS!C:C""))), 0)), ""/d/([a-zA-Z0-9-_]+)"") & ""&idMasterID="" & REGEXEXTRACT($D$6, ""/d/([a-zA-Z0-9-_]+)"") & ""&sheetType="" & ENCODEURL(\'Home Page\'!$B$2), ""Import data using Web App"")"),"Import data using Web App")', None]
  - [None, None, None, None, None, None, None, None, "For that script to work, you must have filled your IDS Master's ID", None]

### Sheet: _IDS
- Dimensions: None rows × None cols
- First non-empty header-like row: 1
- Header values (non-empty): ['=IFERROR(__xludf.DUMMYFUNCTION("IMPORTRANGE(IF(IDS!E6=""✅"", IDS!D6, ""1osjoqKmMwtOWs7Up3e21-3ofN1RHOjsgKV6y3dc6rgE""), ""_IDS!A1:BY212"")"),"Labs")', '=IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),"https://docs.google.com/spreadsheets/d/1yLi6Ni4nZr0Wfct7MmbyNRRi5v6fR62t0kdI-g8NeNo/edit")', '=IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),"✅")', '=IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),"v2.3.2")', '=IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),"WS")', '=IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),"https://docs.google.com/spreadsheets/d/1462mmIeTEmChEYwwpDWacv611QCRW9n-Dvz8oyOQ798/edit")', '=IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),"✅")', '=IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),"v2.2.8")', '=IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),"WS+")', '=IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),"UWs")', '=IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),"https://docs.google.com/spreadsheets/d/1aLEWX2qblJJt96I6QduS_Fp2DjMO6rNToPrUBWGI5BU/edit")', '=IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),"✅")', '=IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),"v2.1.2")', '=IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),"Cards")', '=IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),"https://docs.google.com/spreadsheets/d/1HMQwNLTvcw7aXmjjL7cXmZSdjAF_62ehWpwDIdjqEGs/edit")', '=IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),"✅")', '=IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),"Cards Presets")', '=IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),"v2.2.3")', '=IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),"Relics")', '=IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),"https://docs.google.com/spreadsheets/d/1jtZ_RhMszIY0NzPm-kNhYg_w5D8WDm9tXSJatvVpWDU/edit")', '=IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),"✅")', '=IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),"Vault")', '=IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),"")', '=IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),"Bots")', '=IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),"https://docs.google.com/spreadsheets/d/1gopHNYu4SgI0UbRvscCV4_C1gct7FXr5GBBcjCzCxC0/edit")', '=IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),"✅")', '=IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),"v2.2")', '=IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),"Themes & Songs")', '=IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),"https://docs.google.com/spreadsheets/d/1umYUbdc7TGYJhqFv662Yol9PGzfECdpLYxl4ElV6UwQ/edit")', '=IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),"✅")', '=IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),"Modules")', '=IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),"https://docs.google.com/spreadsheets/d/1mz0hSpsng0Kzlz8xk0VEyRgaE62Gzj5kNLu3Vp-4gGE/edit")', '=IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),"✅")', '=IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),"v5.12")', '=IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),"Guardians")', '=IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),"https://docs.google.com/spreadsheets/d/19vecjglXSr9t51C6vJy-lMGk1xH4h52ytBr-uyKxLcM/edit")', '=IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),"✅")', '=IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),"v2.2.5")']
- Formula cells: 2481 (scanned 20000 cells - truncated)
- Top formulas (up to 10):
  - =IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),"") (count=186)
  - =IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),0.0) (count=171)
  - =IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),99.0) (count=59)
  - =IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),FALSE) (count=54)
  - =IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),20.0) (count=50)
  - =IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),30.0) (count=49)
  - =IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),7.0) (count=46)
  - =IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),1.0) (count=45)
  - =IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),TRUE) (count=36)
  - =IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),9.0) (count=33)
- Preview (first 5 rows × 10 cols):
  - ['=IFERROR(__xludf.DUMMYFUNCTION("IMPORTRANGE(IF(IDS!E6=""✅"", IDS!D6, ""1osjoqKmMwtOWs7Up3e21-3ofN1RHOjsgKV6y3dc6rgE""), ""_IDS!A1:BY212"")"),"Labs")', '=IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),"https://docs.google.com/spreadsheets/d/1yLi6Ni4nZr0Wfct7MmbyNRRi5v6fR62t0kdI-g8NeNo/edit")', '=IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),"✅")', '=IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),"v2.3.2")', '=IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),"WS")', '=IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),"https://docs.google.com/spreadsheets/d/1462mmIeTEmChEYwwpDWacv611QCRW9n-Dvz8oyOQ798/edit")', '=IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),"✅")', '=IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),"v2.2.8")', None, None]
  - ['=IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),"Game Speed")', '=IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),7.0)', '=IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),7.0)', '=IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),7.0)', '=IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),"U")', '=IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),"Workshop Upgrade")', '=IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),"Farming")', None, '=IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),"Tourney")', None]
  - ['=IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),"Starting Cash")', '=IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),6.0)', None, '=IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),99.0)', None, None, '=IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),"¢ Level")', '=IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),"$ Level")', '=IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),"¢ Level")', '=IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),"$ Level")']
  - ['=IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),"Workshop Attack Discount")', '=IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),16.0)', None, '=IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),99.0)', None, '=IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),"Damage")', '=IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),5750.0)', '=IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),6000.0)', '=IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),5750.0)', '=IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),6000.0)']
  - ['=IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),"Workshop Defense Discount")', '=IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),19.0)', None, '=IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),99.0)', None, '=IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),"Attack Speed")', '=IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),99.0)', '=IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),99.0)', '=IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),99.0)', '=IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),99.0)']

### Sheet: Master Sheet
- Dimensions: None rows × None cols
- First non-empty header-like row: 1
- Header values (non-empty): ['Bot', 'Attribute', 'Level', 'Spent', '=IF(\'_IDS\'!C1="✅", HYPERLINK(\'_IDS\'!B1, "Go to my Laboratory Sheet"), "Labs")', 'Level', 'Max', '=IF(\'_IDS\'!BD1="✅", HYPERLINK(\'_IDS\'!BC1, "Go to my Modules Sheet"), "Module")']
- Formula cells: 60 (scanned 442 cells)
- Top formulas (up to 10):
  - =IF('_IDS'!C1="✅", HYPERLINK('_IDS'!B1, "Go to my Laboratory Sheet"), "Labs") (count=1)
  - =IF('_IDS'!BD1="✅", HYPERLINK('_IDS'!BC1, "Go to my Modules Sheet"), "Module") (count=1)
  - =DVT_BOT_STAT(C2, E2, LEFT(G2, 2)) (count=1)
  - =IDS_BOT_CUMMULATED_COST($C$2,E2) (count=1)
  - =IDS_LAB_LEVEL(J2) (count=1)
  - =DVT_BOT_STAT(C2, E3, LEFT(G3, 2)) (count=1)
  - =IDS_BOT_CUMMULATED_COST($C$2,E3) (count=1)
  - =IDS_LAB_LEVEL(J3) (count=1)
  - =DVT_BOT_STAT(C2, E4, LEFT(G4, 2)) (count=1)
  - =IDS_BOT_CUMMULATED_COST($C$2,E4) (count=1)
- Preview (first 5 rows × 10 cols):
  - [None, 'Bot', None, None, 'Attribute', None, 'Level', 'Spent', None, '=IF(\'_IDS\'!C1="✅", HYPERLINK(\'_IDS\'!B1, "Go to my Laboratory Sheet"), "Labs")']
  - ['BOTS', None, 'Flame Bot', None, 'Damage R.', '=DVT_BOT_STAT(C2, E2, LEFT(G2, 2))', '07 | 41% | Cost 340 ⧓ | Next 380 ⧓', '=IDS_BOT_CUMMULATED_COST($C$2,E2)', 'OTHERS', 'Flame Bot - Cooldown']
  - [None, None, None, None, 'Cooldown', '=DVT_BOT_STAT(C2, E3, LEFT(G3, 2))', '09 | 48s | Cost 420 ⧓ | Next 460 ⧓', '=IDS_BOT_CUMMULATED_COST($C$2,E3)', None, 'Thunder Bot - Cooldown']
  - [None, None, None, None, 'Damage', '=DVT_BOT_STAT(C2, E4, LEFT(G4, 2))', '00 | x50 | Cost 0 ⧓ | Next 100 ⧓', '=IDS_BOT_CUMMULATED_COST($C$2,E4)', None, 'Gold Bot - Cooldown']
  - [None, None, True, '=IF(C5,"Unlocked", "Locked")', 'Range', '=DVT_BOT_STAT(C2, E5, LEFT(G5, 2))', '03 | 42m | Cost 180 ⧓ | Next 220 ⧓', '=IDS_BOT_CUMMULATED_COST($C$2,E5)', None, 'Amp Bot - Cooldown']

### Sheet: Golden Bot Path
- Dimensions: None rows × None cols
- First non-empty header-like row: 3
- Header values (non-empty): ['Range', 'GOLDEN BOT PATH', 'UPDATE RUNNING', 'Bonus', 'SIMULATIONS', 'TIME USAGE vs GAIN', 'MATRIX']
- Formula cells: 1350 (scanned 2775 cells)
- Top formulas (up to 10):
  - =IFERROR(__xludf.DUMMYFUNCTION("IF(F6<>"""", SPARKLINE(J5:J35), ""Completed ! 🎉"")"),"") (count=1)
  - =U5 (count=1)
  - =MATCH('Master Sheet'!G10, DVT_BOT_UG_GB_DUR, 0)-2 (count=1)
  - =MATCH('Master Sheet'!G11, DVT_BOT_UG_GB_CD, 0)-2 (count=1)
  - =MATCH('Master Sheet'!G12, DVT_BOT_UG_GB_BONUS, 0)-2 (count=1)
  - =MATCH('Master Sheet'!G13, DVT_BOT_UG_GB_RANGE, 0)-2 (count=1)
  - =LET(
  Duration, 20 + $O5*0.5 + 'Master Sheet'!$K$8 * 0.5,
  Cooldown, 120 - $P5*3 - 'Master Sheet'!$K$4,
  Bonus, 2 + $Q5*0.2,
  Range, 20+$R5*2+'Master Sheet'!$K$12+'Master Sheet'!$K$15+$T$6,

(Bonus-1)*(Duration/Cooldown)*((Range^2)/($T$8^2))) (count=1)
  - =IF(O5>=30, "", LET(
  Duration, 20 + ($O5+1)*0.5 + 'Master Sheet'!$K$8 * 0.5,
  Cooldown, 120 - $P5*3 - 'Master Sheet'!$K$4,
  Bonus, 2 + $Q5*0.2,
  Range, 20+$R5*2+'Master Sheet'!$K$12+'Master Sheet'!$K$15+$T$6,

(Bonus-1)*(Duration/Cooldown)*((Range^2)/($T$8^2)))) (count=1)
  - =IF(P5>=15, "", LET(
  Duration, 20 + $O5*0.5 + 'Master Sheet'!$K$8 * 0.5,
  Cooldown, 120 - ($P5+1)*3 - 'Master Sheet'!$K$4,
  Bonus, 2 + $Q5*0.2,
  Range, 20+$R5*2+'Master Sheet'!$K$12+'Master Sheet'!$K$15+$T$6,

(Bonus-1)*(Duration/Cooldown)*((Range^2)/($T$8^2)))) (count=1)
  - =IF(Q5>=30, "", LET(
  Duration, 20 + $O5*0.5 + 'Master Sheet'!$K$8 * 0.5,
  Cooldown, 120 - $P5*3 - 'Master Sheet'!$K$4,
  Bonus, 2 + ($Q5+1)*0.2,
  Range, 20+$R5*2+'Master Sheet'!$K$12+'Master Sheet'!$K$15+$T$6,

(Bonus-1)*(Duration/Cooldown)*((Range^2)/($T$8^2)))) (count=1)
- Preview (first 5 rows × 10 cols):
  - [None, None, None, None, None, None, None, None, None, None]
  - [None, None, None, None, None, '=IFERROR(__xludf.DUMMYFUNCTION("IF(F6<>"""", SPARKLINE(J5:J35), ""Completed ! 🎉"")"),"")', None, None, None, None]
  - [None, None, 'Range', None, 'GOLDEN BOT PATH', None, None, None, None, None]
  - [None, None, 'Bonus', None, None, 'Upgrade', 'Level', 'Cost', 'ROI / Medals', 'Final Bonus']
  - [None, None, 'Cooldown', None, None, None, None, None, None, None]

### Sheet: DVT_Bot
- Dimensions: None rows × None cols
- First non-empty header-like row: 1
- Header values (non-empty): ['DVT_BOT_UG_FB_DMGR', 'DVT_BOT_UG_FB_CD', 'DVT_BOT_UG_FB_DMG', 'DVT_BOT_UG_FB_RANGE', 'Flame Bot', 'DVT_BOT_UG_TB_DUR', 'DVT_BOT_UG_TB_CD', 'DVT_BOT_UG_TB_LINGER', 'DVT_BOT_UG_TB_RANGE', 'Thunder Bot', 'DVT_BOT_UG_GB_DUR', 'DVT_BOT_UG_GB_CD', 'DVT_BOT_UG_GB_BONUS', 'DVT_BOT_UG_GB_RANGE', 'Golden Bot', 'DVT_BOT_UG_AB_DUR', 'DVT_BOT_UG_AB_CD', 'DVT_BOT_UG_AB_BONUS', 'DVT_BOT_UG_AB_RANGE', 'Amplify Bot']
- Formula cells: 371 (scanned 20000 cells - truncated)
- Top formulas (up to 10):
  - =TEXT(G4,"00") & " | " & TEXT(H4*100, "0") & "% | Cost " & I4 & " ⧓ |" & IF(I5="Max", " Maxed", " Next " & I5 & " ⧓") (count=1)
  - =TEXT(G4,"00") & " | " & TEXT(J4, "0") & "s | Cost " & K4 & " ⧓ |" & IF(K5="Max", " Maxed", " Next " & K5 & " ⧓") (count=1)
  - =TEXT(G4,"00") & " | " & TEXT(L4, "x0") & " | Cost " & M4 & " ⧓ |" & IF(M5="Max", " Maxed", " Next " & M5 & " ⧓") (count=1)
  - =TEXT(G4,"00") & " | " & TEXT(N4, "0") & "m | Cost " & O4 & " ⧓ |" & IF(O5="Max", " Maxed", " Next " & O5 & " ⧓") (count=1)
  - =TEXT(U4,"00") & " | " & TEXT(V4, "0.0") & "s | Cost " & W4 & " ⧓ |" & IF(W5="Max", " Maxed", " Next " & W5 & " ⧓") (count=1)
  - =TEXT(U4,"00") & " | " & TEXT(X4, "0") & "s | Cost " & Y4 & " ⧓ |" & IF(Y5="Max", " Maxed", " Next " & Y5 & " ⧓") (count=1)
  - =TEXT(U4,"00") & " | " & TEXT(Z4*100, "0") & "% | Cost " & AA4 & " ⧓ |" & IF(AA5="Max", " Maxed", " Next " & AA5 & " ⧓") (count=1)
  - =TEXT(U4,"00") & " | " & TEXT(AB4, "0") & "m | Cost " & AC4 & " ⧓ |" & IF(AC5="Max", " Maxed", " Next " & AC5 & " ⧓") (count=1)
  - =TEXT(AI4,"00") & " | " & TEXT(AJ4, "0.0") & "s | Cost " & AK4 & " ⧓ |" & IF(AK5="Max", " Maxed", " Next " & AK5 & " ⧓") (count=1)
  - =TEXT(AI4,"00") & " | " & TEXT(AL4, "0") & "s | Cost " & AM4 & " ⧓ |" & IF(AM5="Max", " Maxed", " Next " & AM5 & " ⧓") (count=1)
- Preview (first 5 rows × 10 cols):
  - [None, None, 'DVT_BOT_UG_FB_DMGR', 'DVT_BOT_UG_FB_CD', 'DVT_BOT_UG_FB_DMG', 'DVT_BOT_UG_FB_RANGE', None, 'Flame Bot', None, None]
  - ['BOTS', 'FLAME BOT', None, None, None, None, None, 'Damage R.', 'Cost', 'Cooldown']
  - [None, None, None, None, None, None, None, 'Locked', 0.0, 'Locked']
  - [None, None, '=TEXT(G4,"00") & " | " & TEXT(H4*100, "0") & "% | Cost " & I4 & " ⧓ |" & IF(I5="Max", " Maxed", " Next " & I5 & " ⧓")', '=TEXT(G4,"00") & " | " & TEXT(J4, "0") & "s | Cost " & K4 & " ⧓ |" & IF(K5="Max", " Maxed", " Next " & K5 & " ⧓")', '=TEXT(G4,"00") & " | " & TEXT(L4, "x0") & " | Cost " & M4 & " ⧓ |" & IF(M5="Max", " Maxed", " Next " & M5 & " ⧓")', '=TEXT(G4,"00") & " | " & TEXT(N4, "0") & "m | Cost " & O4 & " ⧓ |" & IF(O5="Max", " Maxed", " Next " & O5 & " ⧓")', 0.0, 0.2, 0.0, 75.0]
  - [None, None, '=TEXT(G5,"00") & " | " & TEXT(H5*100, "0") & "% | Cost " & I5 & " ⧓ |" & IF(I6="Max", " Maxed", " Next " & I6 & " ⧓")', '=TEXT(G5,"00") & " | " & TEXT(J5, "0") & "s | Cost " & K5 & " ⧓ |" & IF(K6="Max", " Maxed", " Next " & K6 & " ⧓")', '=TEXT(G5,"00") & " | " & TEXT(L5, "x0") & " | Cost " & M5 & " ⧓ |" & IF(M6="Max", " Maxed", " Next " & M6 & " ⧓")', '=TEXT(G5,"00") & " | " & TEXT(N5, "0") & "m | Cost " & O5 & " ⧓ |" & IF(O6="Max", " Maxed", " Next " & O6 & " ⧓")', 1.0, 0.23, 100.0, 72.0]

### Sheet: Amplify Bot Path
- Dimensions: None rows × None cols
- First non-empty header-like row: 3
- Header values (non-empty): ['Range', 'AMPLIFY BOT PATH', 'UPDATE RUNNING', 'Bonus', 'SIMULATIONS', 'TIME USAGE vs GAIN', 'MATRIX']
- Formula cells: 1349 (scanned 2775 cells)
- Top formulas (up to 10):
  - =IFERROR(__xludf.DUMMYFUNCTION("IF(F6<>"""", SPARKLINE(J5:J35), ""Completed ! 🎉"")"),"") (count=1)
  - =U5 (count=1)
  - =MATCH('Master Sheet'!G14, DVT_BOT_UG_AB_DUR, 0)-2 (count=1)
  - =MATCH('Master Sheet'!G15, DVT_BOT_UG_AB_CD, 0)-2 (count=1)
  - =MATCH('Master Sheet'!G16, DVT_BOT_UG_AB_BONUS, 0)-2 (count=1)
  - =MATCH('Master Sheet'!G17, DVT_BOT_UG_AB_RANGE, 0)-2 (count=1)
  - =LET(
  Duration, 20 + $O5*0.5 + 'Master Sheet'!$K$9 * 0.5,
  Cooldown, 120 - $P5*3 - 'Master Sheet'!$K$5,
  Bonus, 3.5 + $Q5*0.4,
  Range, 25+$R5*2+'Master Sheet'!$K$12+'Master Sheet'!$K$15+$T$6,

(Bonus-1)*(Duration/Cooldown)*((Range^2)/($T$8^2))) (count=1)
  - =IF(O5>=30, "", LET(
  Duration, 20 + ($O5+1)*0.5 + 'Master Sheet'!$K$9 * 0.5,
  Cooldown, 120 - $P5*3 - 'Master Sheet'!$K$5,
  Bonus, 3.5 + $Q5*0.4,
  Range, 25+$R5*2+'Master Sheet'!$K$12+'Master Sheet'!$K$15+$T$6,

(Bonus-1)*(Duration/Cooldown)*((Range^2)/($T$8^2)))) (count=1)
  - =IF(P5>=15, "", LET(
  Duration, 20 + $O5*0.5 + 'Master Sheet'!$K$9 * 0.5,
  Cooldown, 120 - ($P5+1)*3 - 'Master Sheet'!$K$5,
  Bonus, 3.5 + $Q5*0.4,
  Range, 25+$R5*2+'Master Sheet'!$K$12+'Master Sheet'!$K$15+$T$6,

(Bonus-1)*(Duration/Cooldown)*((Range^2)/($T$8^2)))) (count=1)
  - =IF(Q5>=30, "", LET(
  Duration, 20 + $O5*0.5 + 'Master Sheet'!$K$9 * 0.5,
  Cooldown, 120 - $P5*3 - 'Master Sheet'!$K$5,
  Bonus, 3.5 + ($Q5+1)*0.4,
  Range, 25+$R5*2+'Master Sheet'!$K$12+'Master Sheet'!$K$15+$T$6,

(Bonus-1)*(Duration/Cooldown)*((Range^2)/($T$8^2)))) (count=1)
- Preview (first 5 rows × 10 cols):
  - [None, None, None, None, None, None, None, None, None, None]
  - [None, None, None, None, None, '=IFERROR(__xludf.DUMMYFUNCTION("IF(F6<>"""", SPARKLINE(J5:J35), ""Completed ! 🎉"")"),"")', None, None, None, None]
  - [None, None, 'Range', None, 'AMPLIFY BOT PATH', None, None, None, None, None]
  - [None, None, 'Bonus', None, None, 'Upgrade', 'Level', 'Cost', 'ROI / Medals', 'Final Bonus']
  - [None, None, 'Cooldown', None, None, None, None, None, None, None]

### Sheet: Thunder Bot Path
- Dimensions: None rows × None cols
- First non-empty header-like row: 3
- Header values (non-empty): ['Range', 'THUNDER BOT PATH', 'UPDATE RUNNING', 'Bonus', 'SIMULATIONS', 'TIME USAGE vs GAIN', 'MATRIX']
- Formula cells: 1349 (scanned 2775 cells)
- Top formulas (up to 10):
  - =IFERROR(__xludf.DUMMYFUNCTION("IF(F6<>"""", SPARKLINE(J5:J35), ""Completed ! 🎉"")"),"") (count=1)
  - =U5 (count=1)
  - =MATCH('Master Sheet'!G6, DVT_BOT_UG_TB_DUR, 0)-2 (count=1)
  - =MATCH('Master Sheet'!G7, DVT_BOT_UG_TB_CD, 0)-2 (count=1)
  - =MATCH('Master Sheet'!G8, DVT_BOT_UG_TB_LINGER, 0)-2 (count=1)
  - =MATCH('Master Sheet'!G9, DVT_BOT_UG_TB_RANGE, 0)-2 (count=1)
  - =LET(
  Duration, 5 + $O5*0.5,
  Cooldown, 120 - $P5*3 - 'Master Sheet'!$K$3,
  Linger, (3+'Master Sheet'!$K$7*0.5)*(0.2 + $Q5*0.03),
  Range, 20+$R5*2+'Master Sheet'!$K$12+'Master Sheet'!$K$15+$T$6,

(((Duration+Linger)/Cooldown)*((Range^2)/($T$8^2)))) (count=1)
  - =IF(O5>=20, "", LET(
  Duration, 5 + ($O5+1)*0.5,
  Cooldown, 120 - $P5*3 - 'Master Sheet'!$K$3,
  Linger, (3+'Master Sheet'!$K$7*0.5)*(0.2 + $Q5*0.03),
  Range, 20+$R5*2+'Master Sheet'!$K$12+'Master Sheet'!$K$15+$T$6,

(((Duration+Linger)/Cooldown)*((Range^2)/($T$8^2))))) (count=1)
  - =IF(P5>=15, "", LET(
  Duration, 5 + $O5*0.5,
  Cooldown, 120 - ($P5+1)*3 - 'Master Sheet'!$K$3,
  Linger, (3+'Master Sheet'!$K$7*0.5)*(0.2 + $Q5*0.03),
  Range, 20+$R5*2+'Master Sheet'!$K$12+'Master Sheet'!$K$15+$T$6,

(((Duration+Linger)/Cooldown)*((Range^2)/($T$8^2))))) (count=1)
  - =IF(Q5>=20, "", LET(
  Duration, 5 + $O5*0.5,
  Cooldown, 120 - $P5*3 - 'Master Sheet'!$K$3,
  Linger, (3+'Master Sheet'!$K$7*0.5)*(0.2 + ($Q5+1)*0.03),
  Range, 20+$R5*2+'Master Sheet'!$K$12+'Master Sheet'!$K$15+$T$6,

(((Duration+Linger)/Cooldown)*((Range^2)/($T$8^2))))) (count=1)
- Preview (first 5 rows × 10 cols):
  - [None, None, None, None, None, None, None, None, None, None]
  - [None, None, None, None, None, '=IFERROR(__xludf.DUMMYFUNCTION("IF(F6<>"""", SPARKLINE(J5:J35), ""Completed ! 🎉"")"),"")', None, None, None, None]
  - [None, None, 'Range', None, 'THUNDER BOT PATH', None, None, None, None, None]
  - [None, None, 'Linger', None, None, 'Upgrade', 'Level', 'Cost', 'ROI / Medals', 'Final Bonus']
  - [None, None, 'Cooldown', None, None, None, None, None, None, None]

### Sheet: All Bots
- Dimensions: None rows × None cols
- First non-empty header-like row: 1
- Header values (non-empty): ['=Sum(C$5:C54)', '=Sum(F$5:F54)', '=Sum(H$5:H54)', '=Sum(J$5:J54)', '=Sum(O$5:O54)', '=Sum(Q$5:Q54)', '=Sum(S$5:S54)', '=Sum(X$5:X54)', '=Sum(Z$5:Z54)', '=Sum(AB$5:AB54)', '=Sum(AG$5:AG54)', '=Sum(AI$5:AI54)', '=Sum(AK$5:AK54)']
- Formula cells: 517 (scanned 2160 cells)
- Top formulas (up to 10):
  - =Sum(C$5:C54) (count=1)
  - =Sum(F$5:F54) (count=1)
  - =Sum(H$5:H54) (count=1)
  - =Sum(J$5:J54) (count=1)
  - =Sum(O$5:O54) (count=1)
  - =Sum(Q$5:Q54) (count=1)
  - =Sum(S$5:S54) (count=1)
  - =Sum(X$5:X54) (count=1)
  - =Sum(Z$5:Z54) (count=1)
  - =Sum(AB$5:AB54) (count=1)
- Preview (first 5 rows × 10 cols):
  - [None, None, '=Sum(C$5:C54)', None, None, '=Sum(F$5:F54)', None, '=Sum(H$5:H54)', None, '=Sum(J$5:J54)']
  - [None, None, None, None, None, None, None, None, None, None]
  - [None, 'Unlock Costs per Bot', None, None, 'Flame Bot', None, None, None, None, None]
  - [None, '# Bots', 'Cost', None, 'Damage R.', 'Cost', 'Cooldown', 'Cost', 'Damage', 'Cost']
  - ['BOT UNLOCKS', 0.0, 0.0, 'FLAME BOT', 0.2, 0.0, 75.0, 0.0, 50.0, 0.0]

### Sheet: GB Cooldowns
- Dimensions: None rows × None cols
- First non-empty header-like row: 4
- Header values (non-empty): ['Labs', 0.0, '=C4+1', '=D4+1', '=E4+1', '=F4+1', '=G4+1', '=H4+1', '=I4+1', '=J4+1', '=K4+1', '=L4+1', '=M4+1', '=N4+1', '=O4+1', '=P4+1', '=Q4+1']
- Formula cells: 488 (scanned 714 cells)
- Top formulas (up to 10):
  - =C4+1 (count=1)
  - =D4+1 (count=1)
  - =E4+1 (count=1)
  - =F4+1 (count=1)
  - =G4+1 (count=1)
  - =H4+1 (count=1)
  - =I4+1 (count=1)
  - =J4+1 (count=1)
  - =K4+1 (count=1)
  - =L4+1 (count=1)
- Preview (first 5 rows × 10 cols):
  - ['', None, None, None, None, None, None, None, None, None]
  - ['Golden Bot Cooldown Table', None, None, None, None, None, None, None, None, None]
  - [None, None, 'Medals', None, None, None, None, None, None, None]
  - [None, 'Labs', 0.0, '=C4+1', '=D4+1', '=E4+1', '=F4+1', '=G4+1', '=H4+1', '=I4+1']
  - [None, 0.0, '=120-3*C$4-$B5', '=120-3*D$4-$B5', '=120-3*E$4-$B5', '=120-3*F$4-$B5', '=120-3*G$4-$B5', '=120-3*H$4-$B5', '=120-3*I$4-$B5', '=120-3*J$4-$B5']

### Sheet: EXPORT
- Dimensions: None rows × None cols
- First non-empty header-like row: 4
- Header values (non-empty): ['Bot', 'Attribute', 'Level']
- Formula cells: 61 (scanned 168 cells)
- Top formulas (up to 10):
  - <openpyxl.worksheet.formula.ArrayFormula object at 0x7ff5833ab940> (count=1)
  - ='Master Sheet'!C2 (count=1)
  - ='Master Sheet'!E2 (count=1)
  - ='Master Sheet'!F2 (count=1)
  - ='Master Sheet'!G2 (count=1)
  - ='Master Sheet'!E3 (count=1)
  - ='Master Sheet'!F3 (count=1)
  - ='Master Sheet'!G3 (count=1)
  - ='Master Sheet'!E4 (count=1)
  - ='Master Sheet'!F4 (count=1)
- Preview (first 5 rows × 10 cols):
  - ['Bv2', None, None, None, None, None, None, None, None, None]
  - [None, 'Medals Spent', None, None, <openpyxl.worksheet.formula.ArrayFormula object at 0x7ff5833a8d90>, None, None, None, None, None]
  - [None, None, None, None, None, None, None, None, None, None]
  - [None, 'Bot', None, None, 'Attribute', None, 'Level', None, None, None]
  - [None, None, "='Master Sheet'!C2", None, "='Master Sheet'!E2", "='Master Sheet'!F2", "='Master Sheet'!G2", None, None, None]
- EXPORT columns (7): ['Bv2', 'Unnamed: 1', 'Unnamed: 2', 'Unnamed: 3', 'Unnamed: 4', 'Unnamed: 5', 'Unnamed: 6']
- EXPORT row count: 19

## Copy of Cards v2.2.3.xlsx
- Size: 527085 bytes
- Sheets: Home Page, DVT_PlayerAndStuff, DVT_Guardians, IDS, _IDS, Master Sheet, Card Preset, EXPORT, EXPORT_PRESET, Card and Mastery Tracker, WAIS Mastery, WS Mastery, RPC Mastery

### Sheet: Home Page
- Dimensions: None rows × None cols
- First non-empty header-like row: 4
- Header values (non-empty): ['=HYPERLINK("https://docs.google.com/spreadsheets/d/1wVLlvWfmcjHRkAnQJzAQu_YZo_eW1FXMVTfYYQnF7Xc/copy", "Cards Initial Link")', 'Sheet Tab', 'Creator', 'Main Contributor', 'Helpers']
- Formula cells: 7 (scanned 372 cells)
- Top formulas (up to 10):
  - =HYPERLINK("https://docs.google.com/spreadsheets/d/1wVLlvWfmcjHRkAnQJzAQu_YZo_eW1FXMVTfYYQnF7Xc/copy", "Cards Initial Link") (count=1)
  - =IFERROR(__xludf.DUMMYFUNCTION("IMPORTRANGE(""1wVLlvWfmcjHRkAnQJzAQu_YZo_eW1FXMVTfYYQnF7Xc"", ""'Home Page'!B12:C13"")"),"v2.2.3") (count=1)
  - =IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),"fix: Card & Mastery Tracker - Wrong total cost") (count=1)
  - =IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),"v2.2") (count=1)
  - =IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),"feat: 22nd gem card slot") (count=1)
  - =IFERROR(__xludf.DUMMYFUNCTION("IMPORTRANGE(""1eCPPuQOE3Pyh8HhnApEMK3RFIutkUjWd61ppVImwWk8"", ""_Giveaway_summary!A1:A2"")"),"⚠️ 2 Giveaway(s) running - 2 Feb | 5 Feb") (count=1)
  - =IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),"Giveaway Details") (count=1)
- Preview (first 5 rows × 10 cols):
  - [None, None, None, None, None, None, None, None, None, None]
  - [None, 'Cards', None, None, None, None, None, None, None, None]
  - [None, None, None, None, None, None, None, None, None, None]
  - [None, '=HYPERLINK("https://docs.google.com/spreadsheets/d/1wVLlvWfmcjHRkAnQJzAQu_YZo_eW1FXMVTfYYQnF7Xc/copy", "Cards Initial Link")', None, None, None, None, 'Sheet Tab', 'Creator', 'Main Contributor', 'Helpers']
  - [None, None, None, None, None, None, None, None, None, None]

### Sheet: DVT_PlayerAndStuff
- Dimensions: None rows × None cols
- First non-empty header-like row: 1
- Header values (non-empty): ['=IFERROR(__xludf.DUMMYFUNCTION("IMPORTRANGE(""1kExWaxZpSizb0KPoFtZdGZI0iBOszTG0LwK-248Saak"", ""DVT_PlayerAndStuff!A1:AA"")"),"")', '=IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),"Daily Missions Rewards")', '=IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),"Daily Missions Box Rewards")', '=IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),"Contribution Rewards")']
- Formula cells: 243 (scanned 690 cells)
- Top formulas (up to 10):
  - =IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),3.0) (count=26)
  - =IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),5.0) (count=13)
  - =IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),10.0) (count=8)
  - =IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),15.0) (count=7)
  - =IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),20.0) (count=7)
  - =IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),25.0) (count=6)
  - =IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),0.0) (count=6)
  - =IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),35.0) (count=6)
  - =IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),30.0) (count=5)
  - =IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),"Coins") (count=3)
- Preview (first 5 rows × 10 cols):
  - ['=IFERROR(__xludf.DUMMYFUNCTION("IMPORTRANGE(""1kExWaxZpSizb0KPoFtZdGZI0iBOszTG0LwK-248Saak"", ""DVT_PlayerAndStuff!A1:AA"")"),"")', None, None, None, '=IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),"Daily Missions Rewards")', None, None, None, '=IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),"Daily Missions Box Rewards")', None]
  - ['=IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),"Tiers")', '=IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),"Tiers")', '=IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),"Tiers+")', '=IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),"Daily Missions")', None, '=IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),"Coins")', '=IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),"Shards")', '=IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),"Gems")', '=IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),"Box")', '=IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),"Mission Required")']
  - [None, '=IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),"Tier 1")', '=IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),"Tier 1")', None, '=IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),"Tier 1")', '=IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),25.0)', '=IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),0.0)', '=IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),3.0)', '=IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),1.0)', '=IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),5.0)']
  - [None, '=IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),"Tier 2")', '=IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),"Tier 1+")', None, '=IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),"Tier 2")', '=IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),100.0)', '=IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),3.0)', '=IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),3.0)', '=IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),2.0)', '=IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),10.0)']
  - [None, '=IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),"Tier 3")', '=IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),"Tier 2")', None, '=IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),"Tier 3")', '=IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),1000.0)', '=IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),5.0)', '=IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),3.0)', '=IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),3.0)', '=IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),15.0)']

### Sheet: DVT_Guardians
- Dimensions: None rows × None cols
- First non-empty header-like row: 1
- Header values (non-empty): ['=IFERROR(__xludf.DUMMYFUNCTION("IMPORTRANGE(""1Q8dhx05NIzgk1JNbZkdL-Y6cX07U09AiFkct4p1tZg4"", ""DVT_Guardians!A1:AS"")"),"")', '=IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),"DVT_GAR_UG_AT_PER")', '=IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),"DVT_GAR_UG_AT_COO")', '=IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),"DVT_GAR_UG_AT_TAR")', '=IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),"Attack")', '=IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),"DVT_GAR_UG_AL_REC")', '=IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),"DVT_GAR_UG_AL_MAX")', '=IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),"DVT_GAR_UG_AL_COO")', '=IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),"Ally")', '=IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),"DVT_GAR_UG_BO_MUL")', '=IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),"DVT_GAR_UG_BO_COO")', '=IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),"DVT_GAR_UG_BO_TAR")', '=IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),"Bounty")', '=IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),"DVT_GAR_UG_FE_COO")', '=IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),"DVT_GAR_UG_FE_FIN")', '=IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),"DVT_GAR_UG_FE_DOU")', '=IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),"Fetch")']
- Formula cells: 2244 (scanned 20000 cells - truncated)
- Top formulas (up to 10):
  - =IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),0.0) (count=28)
  - =IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),60.0) (count=16)
  - =IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),50.0) (count=15)
  - =IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),30.0) (count=15)
  - =IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),40.0) (count=15)
  - =IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),70.0) (count=15)
  - =IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),80.0) (count=15)
  - =IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),90.0) (count=15)
  - =IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),10.0) (count=14)
  - =IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),75.0) (count=14)
- Preview (first 5 rows × 10 cols):
  - ['=IFERROR(__xludf.DUMMYFUNCTION("IMPORTRANGE(""1Q8dhx05NIzgk1JNbZkdL-Y6cX07U09AiFkct4p1tZg4"", ""DVT_Guardians!A1:AS"")"),"")', None, '=IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),"DVT_GAR_UG_AT_PER")', '=IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),"DVT_GAR_UG_AT_COO")', '=IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),"DVT_GAR_UG_AT_TAR")', None, '=IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),"Attack")', None, None, None]
  - ['=IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),"GUARDIANS")', '=IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),"ATTACK")', None, None, None, None, '=IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),"Percentage")', '=IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),"Cost")', '=IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),"Cooldown")', '=IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),"Cost")']
  - [None, None, None, None, None, None, '=IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),"Locked")', '=IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),0.0)', '=IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),"Locked")', '=IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),0.0)']
  - [None, None, '=IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),"00 | 1% | Cost 0 ⧈ | Next 25 ⧈")', '=IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),"00 | 120s | Cost 0 ⧈ | Next 1 ⧈")', '=IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),"00 | 1 | Cost 0 ⧈ | Next 100 ⧈")', '=IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),0.0)', '=IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),0.01)', '=IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),0.0)', '=IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),120.0)', '=IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),0.0)']
  - [None, None, '=IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),"01 | 2% | Cost 25 ⧈ | Next 50 ⧈")', '=IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),"01 | 119s | Cost 1 ⧈ | Next 2 ⧈")', '=IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),"01 | 2 | Cost 100 ⧈ | Next 200 ⧈")', '=IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),1.0)', '=IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),0.02)', '=IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),25.0)', '=IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),119.0)', '=IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),1.0)']

### Sheet: IDS
- Dimensions: None rows × None cols
- First non-empty header-like row: 6
- Header values (non-empty): ["IDS Master's ID       ➡️", '18XbHJtHzu8tjqnP_9JcsZFA6jIwjOKRYmzBzOYBMv2I', '=IFERROR(__xludf.DUMMYFUNCTION("IFERROR(C6.url, IFS(LEFT(C6,8)=""https://"", C6, LEN(C6)=44, ""https://docs.google.com/spreadsheets/d/"" & C6 & ""/edit"", TRUE, C6))"),"https://docs.google.com/spreadsheets/d/18XbHJtHzu8tjqnP_9JcsZFA6jIwjOKRYmzBzOYBMv2I/edit")', '=IFERROR(__xludf.DUMMYFUNCTION("IF(D6<>"""", IF(IMPORTRANGE(D6,""EXPORT!A1"") = F6, ""✅"", ""Wrong ID or Version""), """")"),"✅")', 'v2']
- Formula cells: 4 (scanned 268 cells)
- Top formulas (up to 10):
  - =IFERROR(__xludf.DUMMYFUNCTION("IFERROR(C6.url, IFS(LEFT(C6,8)=""https://"", C6, LEN(C6)=44, ""https://docs.google.com/spreadsheets/d/"" & C6 & ""/edit"", TRUE, C6))"),"https://docs.google.com/spreadsheets/d/18XbHJtHzu8tjqnP_9JcsZFA6jIwjOKRYmzBzOYBMv2I/edit") (count=1)
  - =IFERROR(__xludf.DUMMYFUNCTION("IF(D6<>"""", IF(IMPORTRANGE(D6,""EXPORT!A1"") = F6, ""✅"", ""Wrong ID or Version""), """")"),"✅") (count=1)
  - =HYPERLINK("https://docs.google.com/spreadsheets/d/1osjoqKmMwtOWs7Up3e21-3ofN1RHOjsgKV6y3dc6rgE/copy", "1️⃣ Copy Me") (count=1)
  - =IFS(
  ISERROR(E6), "3️⃣ Click on #REF! and then AUTHORISE ↗",
  E6="", "2️⃣ Please input your IDS Master's ID here ⤴️",
  E6="✅", HYPERLINK(D6, "Go to my IDS Master Sheet"),
  TRUE, "") (count=1)
- Preview (first 5 rows × 10 cols):
  - [None, None, None, None, None, None, None, None, None, None]
  - [None, 'The IDS System', None, None, None, None, None, None, 'Looking for the Import script ? Just run it as you were doing it before, but from IDS Master.\nIt will let you import every new versions at once!', None]
  - [None, None, None, None, None, None, None, None, None, None]
  - [None, 'This Sheet ID is :', '1HMQwNLTvcw7aXmjjL7cXmZSdjAF_62ehWpwDIdjqEGs', None, None, None, None, None, None, None]
  - [None, None, None, None, None, None, None, None, None, None]

### Sheet: _IDS
- Dimensions: None rows × None cols
- First non-empty header-like row: 1
- Header values (non-empty): ['=IFERROR(__xludf.DUMMYFUNCTION("IMPORTRANGE(IF(IDS!E6=""✅"", IDS!D6, ""1osjoqKmMwtOWs7Up3e21-3ofN1RHOjsgKV6y3dc6rgE""), ""_IDS!A1:CE212"")"),"Labs")', '=IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),"https://docs.google.com/spreadsheets/d/1yLi6Ni4nZr0Wfct7MmbyNRRi5v6fR62t0kdI-g8NeNo/edit")', '=IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),"✅")', '=IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),"v2.3.2")', '=IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),"WS")', '=IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),"https://docs.google.com/spreadsheets/d/1462mmIeTEmChEYwwpDWacv611QCRW9n-Dvz8oyOQ798/edit")', '=IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),"✅")', '=IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),"v2.2.8")', '=IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),"WS+")', '=IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),"UWs")', '=IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),"https://docs.google.com/spreadsheets/d/1aLEWX2qblJJt96I6QduS_Fp2DjMO6rNToPrUBWGI5BU/edit")', '=IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),"✅")', '=IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),"v2.1.2")', '=IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),"Cards")', '=IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),"https://docs.google.com/spreadsheets/d/1HMQwNLTvcw7aXmjjL7cXmZSdjAF_62ehWpwDIdjqEGs/edit")', '=IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),"✅")', '=IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),"Cards Presets")', '=IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),"v2.2.3")', '=IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),"Relics")', '=IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),"https://docs.google.com/spreadsheets/d/1jtZ_RhMszIY0NzPm-kNhYg_w5D8WDm9tXSJatvVpWDU/edit")', '=IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),"✅")', '=IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),"Vault")', '=IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),"")', '=IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),"Bots")', '=IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),"https://docs.google.com/spreadsheets/d/1gopHNYu4SgI0UbRvscCV4_C1gct7FXr5GBBcjCzCxC0/edit")', '=IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),"✅")', '=IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),"v2.2")', '=IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),"Themes & Songs")', '=IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),"https://docs.google.com/spreadsheets/d/1umYUbdc7TGYJhqFv662Yol9PGzfECdpLYxl4ElV6UwQ/edit")', '=IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),"✅")', '=IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),"Modules")', '=IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),"https://docs.google.com/spreadsheets/d/1mz0hSpsng0Kzlz8xk0VEyRgaE62Gzj5kNLu3Vp-4gGE/edit")', '=IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),"✅")', '=IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),"v5.12")', '=IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),"Guardians")', '=IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),"https://docs.google.com/spreadsheets/d/19vecjglXSr9t51C6vJy-lMGk1xH4h52ytBr-uyKxLcM/edit")', '=IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),"✅")', '=IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),"v2.2.5")', '=IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),"Player & Stuff")', '=IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),"https://docs.google.com/spreadsheets/d/1fjJxEFt9ZZ5og_q7xHZuyRTf3p_OOUNwCXVV6VtGof0/edit")', '=IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),"✅")', '=IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),"v3.5.2")']
- Formula cells: 2561 (scanned 20000 cells - truncated)
- Top formulas (up to 10):
  - =IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),"") (count=186)
  - =IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),0.0) (count=173)
  - =IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),99.0) (count=59)
  - =IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),FALSE) (count=55)
  - =IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),20.0) (count=50)
  - =IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),30.0) (count=49)
  - =IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),7.0) (count=46)
  - =IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),TRUE) (count=45)
  - =IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),1.0) (count=45)
  - =IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),"Stat") (count=33)
- Preview (first 5 rows × 10 cols):
  - ['=IFERROR(__xludf.DUMMYFUNCTION("IMPORTRANGE(IF(IDS!E6=""✅"", IDS!D6, ""1osjoqKmMwtOWs7Up3e21-3ofN1RHOjsgKV6y3dc6rgE""), ""_IDS!A1:CE212"")"),"Labs")', '=IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),"https://docs.google.com/spreadsheets/d/1yLi6Ni4nZr0Wfct7MmbyNRRi5v6fR62t0kdI-g8NeNo/edit")', '=IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),"✅")', '=IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),"v2.3.2")', '=IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),"WS")', '=IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),"https://docs.google.com/spreadsheets/d/1462mmIeTEmChEYwwpDWacv611QCRW9n-Dvz8oyOQ798/edit")', '=IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),"✅")', '=IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),"v2.2.8")', None, None]
  - ['=IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),"Game Speed")', '=IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),7.0)', '=IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),7.0)', '=IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),7.0)', '=IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),"U")', '=IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),"Workshop Upgrade")', '=IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),"Farming")', None, '=IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),"Tourney")', None]
  - ['=IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),"Starting Cash")', '=IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),6.0)', None, '=IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),99.0)', None, None, '=IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),"¢ Level")', '=IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),"$ Level")', '=IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),"¢ Level")', '=IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),"$ Level")']
  - ['=IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),"Workshop Attack Discount")', '=IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),16.0)', None, '=IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),99.0)', None, '=IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),"Damage")', '=IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),5750.0)', '=IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),6000.0)', '=IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),5750.0)', '=IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),6000.0)']
  - ['=IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),"Workshop Defense Discount")', '=IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),19.0)', None, '=IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),99.0)', None, '=IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),"Attack Speed")', '=IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),99.0)', '=IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),99.0)', '=IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),99.0)', '=IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),99.0)']

### Sheet: Master Sheet
- Dimensions: None rows × None cols
- First non-empty header-like row: 1
- Header values (non-empty): ['Card Name', 'Level', 'Mastery', '=IF(\'_IDS\'!C1="✅", HYPERLINK(\'_IDS\'!B1, "Go to my Laboratory Sheet"), "Labs")', 'Level', 'Max', '=IF(\'_IDS\'!K1="✅", HYPERLINK(\'_IDS\'!J1, "Go to my Workshop Sheet"), "Workshop Upgrade")', '¢ Level', '$ Level', 'Max', '=IF(\'_IDS\'!AD1="✅", HYPERLINK(\'_IDS\'!AC1, "Go to my Modules Sheet"), "Module")', 'Substat', 'Rarity', 'Value', '=IF(\'_IDS\'!$AF$1="✅", HYPERLINK(\'_IDS\'!AE1, "Go to my Vault Sheet"), "Vault")', 'Bonus', 'Guardians', 'Attribute', 'Level']
- Formula cells: 68 (scanned 1320 cells)
- Top formulas (up to 10):
  - =IF('_IDS'!C1="✅", HYPERLINK('_IDS'!B1, "Go to my Laboratory Sheet"), "Labs") (count=1)
  - =IF('_IDS'!K1="✅", HYPERLINK('_IDS'!J1, "Go to my Workshop Sheet"), "Workshop Upgrade") (count=1)
  - =IF('_IDS'!AD1="✅", HYPERLINK('_IDS'!AC1, "Go to my Modules Sheet"), "Module") (count=1)
  - =IF('_IDS'!$AF$1="✅", HYPERLINK('_IDS'!AE1, "Go to my Vault Sheet"), "Vault") (count=1)
  - =IDS_LAB_LEVEL(G2) (count=1)
  - ='_IDS'!G2 (count=1)
  - =IDS_MOD_GENERATOR_SUBSTATS(R5) (count=1)
  - =IDS_VAULT_STAT(X2) (count=1)
  - =DVT_GUARDIAN_STAT(AB2,AD2,LEFT(AF2,2)) (count=1)
  - =IDS_GUARDIAN_LEVEL(AB2,AD2) (count=1)
- Preview (first 5 rows × 10 cols):
  - [None, 'Card Name', 'Level', 'Mastery', None, None, '=IF(\'_IDS\'!C1="✅", HYPERLINK(\'_IDS\'!B1, "Go to my Laboratory Sheet"), "Labs")', 'Level', 'Max', None]
  - ['CARDS', 'Card Slot (Gems)', 15.0, None, 'OTHERS', 'LABS', 'Labs Coin Discount', '=IDS_LAB_LEVEL(G2)', 99.0, 'WORKSHOP']
  - [None, 'Damage', 7.0, False, None, None, 'Damage Mastery', '=IDS_LAB_LEVEL(G3)', 9.0, None]
  - [None, 'Attack Speed', 7.0, False, None, None, 'Attack Speed Mastery', '=IDS_LAB_LEVEL(G4)', 9.0, None]
  - [None, 'Health', 7.0, False, None, None, 'Health Mastery', '=IDS_LAB_LEVEL(G5)', 9.0, None]

### Sheet: Card Preset
- Dimensions: None rows × None cols
- First non-empty header-like row: 2
- Header values (non-empty): [True, 'Remove used cards from the pool', 'Tick the boxes to compare', 'You can rename 3, 4, 5']
- Formula cells: 156 (scanned 858 cells)
- Top formulas (up to 10):
  - ='Card and Mastery Tracker'!D15 (count=1)
  - <openpyxl.worksheet.formula.ArrayFormula object at 0x7ff58312d450> (count=1)
  - <openpyxl.worksheet.formula.ArrayFormula object at 0x7ff58312d510> (count=1)
  - <openpyxl.worksheet.formula.ArrayFormula object at 0x7ff58312d420> (count=1)
  - <openpyxl.worksheet.formula.ArrayFormula object at 0x7ff58312d480> (count=1)
  - <openpyxl.worksheet.formula.ArrayFormula object at 0x7ff58312d330> (count=1)
  - <openpyxl.worksheet.formula.ArrayFormula object at 0x7ff58312d4e0> (count=1)
  - <openpyxl.worksheet.formula.ArrayFormula object at 0x7ff58312d120> (count=1)
  - <openpyxl.worksheet.formula.ArrayFormula object at 0x7ff58312c850> (count=1)
  - <openpyxl.worksheet.formula.ArrayFormula object at 0x7ff58312dc00> (count=1)
- Preview (first 5 rows × 10 cols):
  - [None, None, None, None, None, None, None, None, None, None]
  - [None, None, True, 'Remove used cards from the pool', None, None, None, 'Tick the boxes to compare', None, None]
  - ["='Card and Mastery Tracker'!D15", None, None, False, None, None, None, False, None, None]
  - [None, None, 'Farming', None, None, None, 'Tourney', None, None, None]
  - [None, None, 1.0, 'Enemy Balance', <openpyxl.worksheet.formula.ArrayFormula object at 0x7ff58312e680>, None, 1.0, 'Attack Speed', <openpyxl.worksheet.formula.ArrayFormula object at 0x7ff58312e6b0>, None]

### Sheet: EXPORT
- Dimensions: None rows × None cols
- First non-empty header-like row: 4
- Header values (non-empty): ['Card Name', 'Level', 'Mastery']
- Formula cells: 63 (scanned 180 cells)
- Top formulas (up to 10):
  - ='Master Sheet'!C2 (count=1)
  - ='Master Sheet'!C3 (count=1)
  - ='Master Sheet'!D3 (count=1)
  - ='Master Sheet'!C4 (count=1)
  - ='Master Sheet'!D4 (count=1)
  - ='Master Sheet'!C5 (count=1)
  - ='Master Sheet'!D5 (count=1)
  - ='Master Sheet'!C6 (count=1)
  - ='Master Sheet'!D6 (count=1)
  - ='Master Sheet'!C7 (count=1)
- Preview (first 5 rows × 10 cols):
  - ['Cv2', None, None, None, None, None, None, None, None, None]
  - [None, 'Card Slot (Gems)', "='Master Sheet'!C2", None, None, None, None, None, None, None]
  - [None, None, None, None, None, None, None, None, None, None]
  - [None, 'Card Name', 'Level', 'Mastery', None, None, None, None, None, None]
  - [None, 'Damage', "='Master Sheet'!C3", "='Master Sheet'!D3", None, None, None, None, None, None]
- EXPORT columns (4): ['Cv2', 'Unnamed: 1', 'Unnamed: 2', 'Unnamed: 3']
- EXPORT row count: 34

### Sheet: EXPORT_PRESET
- Dimensions: None rows × None cols
- First non-empty header-like row: 2
- Header values (non-empty): ["='Card Preset'!C4", "='Card Preset'!G4", "='Card Preset'!K4", "='Card Preset'!O4", "='Card Preset'!S4"]
- Formula cells: 10 (scanned 210 cells)
- Top formulas (up to 10):
  - ='Card Preset'!C4 (count=1)
  - ='Card Preset'!G4 (count=1)
  - ='Card Preset'!K4 (count=1)
  - ='Card Preset'!O4 (count=1)
  - ='Card Preset'!S4 (count=1)
  - <openpyxl.worksheet.formula.ArrayFormula object at 0x7ff5831fd480> (count=1)
  - <openpyxl.worksheet.formula.ArrayFormula object at 0x7ff5831fd240> (count=1)
  - <openpyxl.worksheet.formula.ArrayFormula object at 0x7ff5831fd390> (count=1)
  - <openpyxl.worksheet.formula.ArrayFormula object at 0x7ff5831fdfc0> (count=1)
  - <openpyxl.worksheet.formula.ArrayFormula object at 0x7ff5831fceb0> (count=1)
- Preview (first 5 rows × 10 cols):
  - [None, None, None, None, None, None, None, None, None, None]
  - [None, "='Card Preset'!C4", "='Card Preset'!G4", "='Card Preset'!K4", "='Card Preset'!O4", "='Card Preset'!S4", None, None, None, None]
  - [None, <openpyxl.worksheet.formula.ArrayFormula object at 0x7ff5831fc550>, <openpyxl.worksheet.formula.ArrayFormula object at 0x7ff5831fc610>, <openpyxl.worksheet.formula.ArrayFormula object at 0x7ff5831fdb10>, <openpyxl.worksheet.formula.ArrayFormula object at 0x7ff5831fcfa0>, <openpyxl.worksheet.formula.ArrayFormula object at 0x7ff5831fc5b0>, None, None, None, None]
  - [None, 'Extra Defense', 'Damage', None, None, None, None, None, None, None]
  - [None, 'Health', 'Berserker', None, None, None, None, None, None, None]
- EXPORT columns (6): ['Unnamed: 0', 'Unnamed: 1', 'Unnamed: 2', 'Unnamed: 3', 'Unnamed: 4', 'Unnamed: 5']
- EXPORT row count: 16

### Sheet: Card and Mastery Tracker
- Dimensions: None rows × None cols
- First non-empty header-like row: 2
- Header values (non-empty): ['Stones', 750.0, 'Coin Discount', "='Master Sheet'!H2*0.3%"]
- Formula cells: 417 (scanned 980 cells)
- Top formulas (up to 10):
  - ='Master Sheet'!H2*0.3% (count=1)
  - =SUM(N4:N34) (count=1)
  - =IFS(K4="Locked", "Locked", K4=1,"x1.5", K4=2,"x2", K4=3,"x2.4", K4=4,"x2.8", K4=5,"x3.2", K4=6,"x3.6", K4=7,"x4") (count=1)
  - ='Master Sheet'!C3 (count=1)
  - =IFS(K4="Locked", "1", K4=1,"3", K4=2,"5", K4=3,"8", K4=4,"12", K4=5,"20", K4=6,"32", K4=7,"-") (count=1)
  - =IFS(K4="Locked",80-L4,K4=1,80-L4,K4=2,80-3-L4,K4=3,80-8-L4,K4=4,80-16-L4,K4=5,80-28-L4,K4=6,80-48-L4,K4=7,"-")
 (count=1)
  - =IF(M4="-","Done",ROUND((1 - (N4 / 80)) * 100,0) & " %") (count=1)
  - =IF(N4="-", "-",N4*20) (count=1)
  - =IF(W4="-", "", 1+(N(W4)+1)*T4) (count=1)
  - =IF('Master Sheet'!D3, "Purchased", "*") (count=1)
- Preview (first 5 rows × 10 cols):
  - [None, None, None, None, None, None, None, None, None, None]
  - [None, None, None, None, None, None, None, None, None, None]
  - [None, '↓ Gem Costs ↓', 'Cards', None, None, None, 'Lock', 'Card', 'Value', '↓ Cards ↓']
  - [None, None, 'Cards required for Completion', None, '=SUM(N4:N34)', None, None, 'Damage', '=IFS(K4="Locked", "Locked", K4=1,"x1.5", K4=2,"x2", K4=3,"x2.4", K4=4,"x2.8", K4=5,"x3.2", K4=6,"x3.6", K4=7,"x4")', None]
  - [None, None, 'Gems required for Completion', None, '=E4*20', None, None, 'Attack Speed', '=IFS(K5="Locked", "Locked", K5=1,"x1.25", K5=2,"x1.4", K5=3,"x1.55", K5=4,"x1.7", K5=5,"x1.85", K5=6,"x2", K5=7,"x2.15")', None]

### Sheet: WAIS Mastery
- Dimensions: None rows × None cols
- First non-empty header-like row: 2
- Header values (non-empty): [0.1, 0.2, 0.30000000000000004, 0.4, 0.5, 0.6, 0.7, 0.7999999999999999, 0.8999999999999999, 0.9999999999999999, 'None', 'WA', 'IS:', 'WAIS:', 1.0, 2.0, 4.0, 2.0, 3.0]
- Formula cells: 536 (scanned 1248 cells)
- Top formulas (up to 10):
  - =MATCH($C$33,$C$3:$M$3, 0)-1 (count=1)
  - =(RIGHT(C34, 1)+1)*1.8*100 (count=1)
  - =MAX(0, MIN(C5, $E$35)-C4) (count=1)
  - =P4*B4*AE4 (count=1)
  - =MAX(0, MIN(OFFSET(C5, 0, $S$3),$E$35)-OFFSET(C4, 0, $S$3)) (count=1)
  - =R4*B4*AE4 (count=1)
  - =1-SUM(AA4:AD4) (count=1)
  - =Z4+(AA4+AC4)*2+AD4*3+AB4*4 (count=1)
  - =ROUND($C5/(1+D$2),0) (count=1)
  - =ROUND($C5/(1+E$2),0) (count=1)
- Preview (first 5 rows × 10 cols):
  - [None, None, None, None, None, None, None, None, None, None]
  - [None, None, None, 0.1, 0.2, 0.30000000000000004, 0.4, 0.5, 0.6, 0.7]
  - [None, 'Spawn', 'Normal', 'Lvl 0', 'Lvl 1', 'Lvl 2', 'Lvl 3', 'Lvl 4', 'Lvl 5', 'Lvl 6']
  - [None, 10.0, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0]
  - [None, 11.0, 3.0, '=ROUND($C5/(1+D$2),0)', '=ROUND($C5/(1+E$2),0)', '=ROUND($C5/(1+F$2),0)', '=ROUND($C5/(1+G$2),0)', '=ROUND($C5/(1+H$2),0)', '=ROUND($C5/(1+I$2),0)', '=ROUND($C5/(1+J$2),0)']

### Sheet: WS Mastery
- Dimensions: None rows × None cols
- First non-empty header-like row: 5
- Header values (non-empty): ['=SWITCH(B3, "Locked", "9%", 1, "9%", 2, "10%", 3, "11%", 4, "13%", 5, "15%", 6, "17%", 7, "19%", "9%")', 0.0, 0.1, 0.15, 0.2, 0.25, 0.3, 0.35, 0.4, 0.45, 0.5, 0.55, 'Credits']
- Formula cells: 212 (scanned 504 cells)
- Top formulas (up to 10):
  - ='Master Sheet'!C19 (count=1)
  - =IF('Master Sheet'!D19, "Lvl "&'Master Sheet'!H19, "No Mast.") (count=1)
  - =SWITCH(B3, "Locked", "9%", 1, "9%", 2, "10%", 3, "11%", 4, "13%", 5, "15%", 6, "17%", 7, "19%", "9%") (count=1)
  - =$B$5-SUM(C8:C22) (count=1)
  - =$B$5-SUM(D8:D22) (count=1)
  - =$B$5-SUM(E8:E22) (count=1)
  - =$B$5-SUM(F8:F22) (count=1)
  - =$B$5-SUM(G8:G22) (count=1)
  - =$B$5-SUM(H8:H22) (count=1)
  - =$B$5-SUM(I8:I22) (count=1)
- Preview (first 5 rows × 10 cols):
  - [None, None, None, None, None, None, None, None, None, None]
  - [None, 'Wave Skip Level', None, 'Wave Skip Mastery', None, None, None, None, None, None]
  - [None, "='Master Sheet'!C19", None, '=IF(\'Master Sheet\'!D19, "Lvl "&\'Master Sheet\'!H19, "No Mast.")', None, None, None, None, None, None]
  - [None, None, None, None, None, None, None, None, None, None]
  - [None, '=SWITCH(B3, "Locked", "9%", 1, "9%", 2, "10%", 3, "11%", 4, "13%", 5, "15%", 6, "17%", 7, "19%", "9%")', 0.0, 0.1, 0.15, 0.2, 0.25, 0.3, 0.35, 0.4]

### Sheet: RPC Mastery
- Dimensions: None rows × None cols
- First non-empty header-like row: 3
- Header values (non-empty): ['Package Chance', 'Lab Level:', "='Master Sheet'!H34", 'Ws Level:', "='Master Sheet'!L3", 'Card Lvl:', "=N('Master Sheet'!C22)", 'Substats:', '=IFERROR(VLOOKUP("Package Chance", \'Master Sheet\'!S2:V9, 4, FALSE), 0)', '=IFERROR(VLOOKUP("Package Chance", \'Master Sheet\'!S10:V17, 4, FALSE), 0)*(\'Master Sheet\'!R16+\'Master Sheet\'!H39/100)', 'Total:', '=LET(\n  WS, 6%+0.4%*H3,\n  Lab, F3*0.2%,\n  Card, IF(IDS_CARDS_IN_PRESET(\'Card Preset\'!C4, "Recovery Package Chance"), 12% + J3 * 3%, 0),\n  Substat, L3+M3,\n\nWS + Lab + Card + Substat)']
- Formula cells: 526 (scanned 5376 cells)
- Top formulas (up to 10):
  - =0 (count=2)
  - =1 (count=2)
  - ='Master Sheet'!H34 (count=1)
  - ='Master Sheet'!L3 (count=1)
  - =N('Master Sheet'!C22) (count=1)
  - =IFERROR(VLOOKUP("Package Chance", 'Master Sheet'!S2:V9, 4, FALSE), 0) (count=1)
  - =IFERROR(VLOOKUP("Package Chance", 'Master Sheet'!S10:V17, 4, FALSE), 0)*('Master Sheet'!R16+'Master Sheet'!H39/100) (count=1)
  - =LET(
  WS, 6%+0.4%*H3,
  Lab, F3*0.2%,
  Card, IF(IDS_CARDS_IN_PRESET('Card Preset'!C4, "Recovery Package Chance"), 12% + J3 * 3%, 0),
  Substat, L3+M3,

WS + Lab + Card + Substat) (count=1)
  - ='Master Sheet'!AE2 (count=1)
  - ='Master Sheet'!AE3 (count=1)
- Preview (first 5 rows × 10 cols):
  - [None, None, None, None, None, None, None, None, None, None]
  - [None, 'Estimated total daily shards (Missions, Boss drops, and RPC; not including purchases, or fleets)', None, None, None, None, None, None, None, None]
  - [None, 'Package Chance', None, None, 'Lab Level:', "='Master Sheet'!H34", 'Ws Level:', "='Master Sheet'!L3", 'Card Lvl:', "=N('Master Sheet'!C22)"]
  - [None, 'Fetch', None, None, 'Cooldown:', "='Master Sheet'!AE2", 'Find %:', "='Master Sheet'!AE3", 'Dbl Find %:', "='Master Sheet'!AE4"]
  - [None, 'Assumes package after boss lab is maxed', None, None, None, 'Common Drop Lab:', None, "='Master Sheet'!H35", '=H5*0.3%', '=I5*5+I6*10']

## Copy of Effective Paths v5.00.01.xlsx
- Size: 2 bytes
- NOTE: file appears empty or invalid for XLSX parsing.

## Copy of Guardians v2.2.5.xlsx
- Size: 840023 bytes
- Sheets: Home Page, _IDS, IDS, Master Sheet, Attack Path, Ally Path, Bounty Path, Fetch Path, EXPORT, DVT_Guardians, Summon Path, All Chips

### Sheet: Home Page
- Dimensions: None rows × None cols
- First non-empty header-like row: 4
- Header values (non-empty): ['=HYPERLINK("https://docs.google.com/spreadsheets/d/1Q8dhx05NIzgk1JNbZkdL-Y6cX07U09AiFkct4p1tZg4/copy", "Guardians Initial Link")', 'Sheet Tab', 'Main Contributor', 'Helpers']
- Formula cells: 5 (scanned 286 cells)
- Top formulas (up to 10):
  - =HYPERLINK("https://docs.google.com/spreadsheets/d/1Q8dhx05NIzgk1JNbZkdL-Y6cX07U09AiFkct4p1tZg4/copy", "Guardians Initial Link") (count=1)
  - =IFERROR(__xludf.DUMMYFUNCTION("IMPORTRANGE(""1Q8dhx05NIzgk1JNbZkdL-Y6cX07U09AiFkct4p1tZg4"", ""'Home Page'!B12:C13"")"),"v2.3") (count=1)
  - =IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),"feat: New Chip - Scout") (count=1)
  - =IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),"v2.2.5") (count=1)
  - =IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),"feat: Fetch current rewards") (count=1)
- Preview (first 5 rows × 10 cols):
  - [None, None, None, None, None, None, None, None, None, None]
  - [None, 'Guardians', None, None, None, None, None, None, None, None]
  - [None, None, None, None, None, None, None, None, None, None]
  - [None, '=HYPERLINK("https://docs.google.com/spreadsheets/d/1Q8dhx05NIzgk1JNbZkdL-Y6cX07U09AiFkct4p1tZg4/copy", "Guardians Initial Link")', None, None, None, None, 'Sheet Tab', 'Main Contributor', 'Helpers', None]
  - [None, None, None, None, None, None, None, None, None, None]

### Sheet: _IDS
- Dimensions: None rows × None cols
- First non-empty header-like row: 1
- Header values (non-empty): ['=IFERROR(__xludf.DUMMYFUNCTION("IMPORTRANGE(IF(IDS!E6=""✅"", IDS!D6, ""1osjoqKmMwtOWs7Up3e21-3ofN1RHOjsgKV6y3dc6rgE""), ""_IDS!A1:BY212"")"),"Labs")', '=IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),"https://docs.google.com/spreadsheets/d/1yLi6Ni4nZr0Wfct7MmbyNRRi5v6fR62t0kdI-g8NeNo/edit")', '=IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),"✅")', '=IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),"v2.3.2")', '=IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),"WS")', '=IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),"https://docs.google.com/spreadsheets/d/1462mmIeTEmChEYwwpDWacv611QCRW9n-Dvz8oyOQ798/edit")', '=IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),"✅")', '=IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),"v2.2.8")', '=IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),"WS+")', '=IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),"UWs")', '=IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),"https://docs.google.com/spreadsheets/d/1aLEWX2qblJJt96I6QduS_Fp2DjMO6rNToPrUBWGI5BU/edit")', '=IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),"✅")', '=IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),"v2.1.2")', '=IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),"Cards")', '=IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),"https://docs.google.com/spreadsheets/d/1HMQwNLTvcw7aXmjjL7cXmZSdjAF_62ehWpwDIdjqEGs/edit")', '=IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),"✅")', '=IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),"Cards Presets")', '=IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),"v2.2.3")', '=IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),"Relics")', '=IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),"https://docs.google.com/spreadsheets/d/1jtZ_RhMszIY0NzPm-kNhYg_w5D8WDm9tXSJatvVpWDU/edit")', '=IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),"✅")', '=IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),"Vault")', '=IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),"")', '=IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),"Bots")', '=IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),"https://docs.google.com/spreadsheets/d/1gopHNYu4SgI0UbRvscCV4_C1gct7FXr5GBBcjCzCxC0/edit")', '=IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),"✅")', '=IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),"v2.2")', '=IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),"Themes & Songs")', '=IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),"https://docs.google.com/spreadsheets/d/1umYUbdc7TGYJhqFv662Yol9PGzfECdpLYxl4ElV6UwQ/edit")', '=IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),"✅")', '=IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),"Modules")', '=IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),"https://docs.google.com/spreadsheets/d/1mz0hSpsng0Kzlz8xk0VEyRgaE62Gzj5kNLu3Vp-4gGE/edit")', '=IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),"✅")', '=IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),"v5.12")', '=IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),"Guardians")', '=IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),"https://docs.google.com/spreadsheets/d/19vecjglXSr9t51C6vJy-lMGk1xH4h52ytBr-uyKxLcM/edit")', '=IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),"✅")', '=IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),"v2.2.5")']
- Formula cells: 2481 (scanned 20000 cells - truncated)
- Top formulas (up to 10):
  - =IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),"") (count=186)
  - =IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),0.0) (count=171)
  - =IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),99.0) (count=59)
  - =IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),FALSE) (count=54)
  - =IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),20.0) (count=50)
  - =IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),30.0) (count=49)
  - =IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),7.0) (count=46)
  - =IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),1.0) (count=45)
  - =IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),TRUE) (count=36)
  - =IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),9.0) (count=33)
- Preview (first 5 rows × 10 cols):
  - ['=IFERROR(__xludf.DUMMYFUNCTION("IMPORTRANGE(IF(IDS!E6=""✅"", IDS!D6, ""1osjoqKmMwtOWs7Up3e21-3ofN1RHOjsgKV6y3dc6rgE""), ""_IDS!A1:BY212"")"),"Labs")', '=IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),"https://docs.google.com/spreadsheets/d/1yLi6Ni4nZr0Wfct7MmbyNRRi5v6fR62t0kdI-g8NeNo/edit")', '=IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),"✅")', '=IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),"v2.3.2")', '=IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),"WS")', '=IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),"https://docs.google.com/spreadsheets/d/1462mmIeTEmChEYwwpDWacv611QCRW9n-Dvz8oyOQ798/edit")', '=IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),"✅")', '=IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),"v2.2.8")', None, None]
  - ['=IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),"Game Speed")', '=IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),7.0)', '=IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),7.0)', '=IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),7.0)', '=IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),"U")', '=IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),"Workshop Upgrade")', '=IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),"Farming")', None, '=IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),"Tourney")', None]
  - ['=IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),"Starting Cash")', '=IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),6.0)', None, '=IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),99.0)', None, None, '=IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),"¢ Level")', '=IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),"$ Level")', '=IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),"¢ Level")', '=IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),"$ Level")']
  - ['=IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),"Workshop Attack Discount")', '=IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),16.0)', None, '=IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),99.0)', None, '=IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),"Damage")', '=IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),5750.0)', '=IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),6000.0)', '=IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),5750.0)', '=IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),6000.0)']
  - ['=IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),"Workshop Defense Discount")', '=IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),19.0)', None, '=IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),99.0)', None, '=IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),"Attack Speed")', '=IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),99.0)', '=IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),99.0)', '=IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),99.0)', '=IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),99.0)']

### Sheet: IDS
- Dimensions: None rows × None cols
- First non-empty header-like row: 6
- Header values (non-empty): ["IDS Master's ID       ➡️", '18XbHJtHzu8tjqnP_9JcsZFA6jIwjOKRYmzBzOYBMv2I', '=IFERROR(__xludf.DUMMYFUNCTION("IFERROR(C6.url, IFS(LEFT(C6,8)=""https://"", C6, LEN(C6)=44, ""https://docs.google.com/spreadsheets/d/"" & C6 & ""/edit"", TRUE, C6))"),"https://docs.google.com/spreadsheets/d/18XbHJtHzu8tjqnP_9JcsZFA6jIwjOKRYmzBzOYBMv2I/edit")', '=IFERROR(__xludf.DUMMYFUNCTION("IF(D6<>"""", IF(IMPORTRANGE(D6,""EXPORT!A1"") = F6, ""✅"", ""Wrong ID or Version""), """")"),"✅")', 'v2']
- Formula cells: 4 (scanned 268 cells)
- Top formulas (up to 10):
  - =IFERROR(__xludf.DUMMYFUNCTION("IFERROR(C6.url, IFS(LEFT(C6,8)=""https://"", C6, LEN(C6)=44, ""https://docs.google.com/spreadsheets/d/"" & C6 & ""/edit"", TRUE, C6))"),"https://docs.google.com/spreadsheets/d/18XbHJtHzu8tjqnP_9JcsZFA6jIwjOKRYmzBzOYBMv2I/edit") (count=1)
  - =IFERROR(__xludf.DUMMYFUNCTION("IF(D6<>"""", IF(IMPORTRANGE(D6,""EXPORT!A1"") = F6, ""✅"", ""Wrong ID or Version""), """")"),"✅") (count=1)
  - =HYPERLINK("https://docs.google.com/spreadsheets/d/1osjoqKmMwtOWs7Up3e21-3ofN1RHOjsgKV6y3dc6rgE/copy", "1️⃣ Copy Me") (count=1)
  - =IFS(
  ISERROR(E6), "3️⃣ Click on #REF! and then AUTHORISE ↗",
  E6="", "2️⃣ Please input your IDS Master's ID here ⤴️",
  E6="✅", HYPERLINK(D6, "Go to my IDS Master Sheet"),
  TRUE, "") (count=1)
- Preview (first 5 rows × 10 cols):
  - [None, None, None, None, None, None, None, None, None, None]
  - [None, 'The IDS System', None, None, None, None, None, None, 'Looking for the Import script ? Just run it as you were doing it before, but from IDS Master.\nIt will let you import every new versions at once!', None]
  - [None, None, None, None, None, None, None, None, None, None]
  - [None, 'This Sheet ID is :', '19vecjglXSr9t51C6vJy-lMGk1xH4h52ytBr-uyKxLcM', None, None, None, None, None, None, None]
  - [None, None, None, None, None, None, None, None, None, None]

### Sheet: Master Sheet
- Dimensions: None rows × None cols
- First non-empty header-like row: 1
- Header values (non-empty): ['Chips', 'Attribute', 'Level', 'Bits']
- Formula cells: 39 (scanned 171 cells)
- Top formulas (up to 10):
  - =DVT_GUARDIAN_STAT(B2, D2, LEFT(F2, 2)) (count=1)
  - =DVT_GUARDIAN_CUMULATED_COST(B2,D2,LEFT(F2, 2)) (count=1)
  - =SUM(G2:G4) (count=1)
  - =DVT_GUARDIAN_STAT(B2, D3, LEFT(F3, 2)) (count=1)
  - =DVT_GUARDIAN_CUMULATED_COST(B2,D3,LEFT(F3, 2)) (count=1)
  - =DVT_GUARDIAN_STAT(B2, D4, LEFT(F4, 2)) (count=1)
  - =DVT_GUARDIAN_CUMULATED_COST(B2,D4,LEFT(F4, 2)) (count=1)
  - =DVT_GUARDIAN_STAT(B5, D5, LEFT(F5, 2)) (count=1)
  - =DVT_GUARDIAN_CUMULATED_COST(B5,D5,LEFT(F5, 2)) (count=1)
  - =SUM(G5:G7) (count=1)
- Preview (first 5 rows × 10 cols):
  - ['Chips', None, None, 'Attribute', None, 'Level', 'Bits', None, None, None]
  - [None, 'Attack', None, 'Percentage', '=DVT_GUARDIAN_STAT(B2, D2, LEFT(F2, 2))', '00 | 1% | Cost 0 ⧈ | Next 25 ⧈', '=DVT_GUARDIAN_CUMULATED_COST(B2,D2,LEFT(F2, 2))', '=SUM(G2:G4)', None, None]
  - [None, None, None, 'Cooldown', '=DVT_GUARDIAN_STAT(B2, D3, LEFT(F3, 2))', '00 | 120s | Cost 0 ⧈ | Next 1 ⧈', '=DVT_GUARDIAN_CUMULATED_COST(B2,D3,LEFT(F3, 2))', None, None, None]
  - [None, None, 'Unlocked', 'Targets', '=DVT_GUARDIAN_STAT(B2, D4, LEFT(F4, 2))', '00 | 1 | Cost 0 ⧈ | Next 100 ⧈', '=DVT_GUARDIAN_CUMULATED_COST(B2,D4,LEFT(F4, 2))', None, None, None]
  - [None, 'Ally', None, 'Recovery Amount', '=DVT_GUARDIAN_STAT(B5, D5, LEFT(F5, 2))', '00 | 1% | Cost 0 ⧈ | Next 10 ⧈', '=DVT_GUARDIAN_CUMULATED_COST(B5,D5,LEFT(F5, 2))', '=SUM(G5:G7)', None, None]

### Sheet: Attack Path
- Dimensions: None rows × None cols
- First non-empty header-like row: 3
- Header values (non-empty): ['Percentage', '=COUNTA(DVT_GAR_UG_AT_PER)-1', 'ATTACK PATH', 'v0.27', 'LAB PATH UPDATE RUNNING', 'eEcon SIMULATIONS', 'TIME USAGE VS eEcon GAIN', 'LAB PATH UPDATE MATRIX']
- Formula cells: 1906 (scanned 3936 cells)
- Top formulas (up to 10):
  - =COUNTA(DVT_GAR_UG_AT_PER)-1 (count=1)
  - =COUNTA(DVT_GAR_UG_AT_COO)-1 (count=1)
  - =COUNTA(DVT_GAR_UG_AT_TAR)-1 (count=1)
  - =S5 (count=1)
  - =IDS_GUARDIAN_ATTACK_PERCENTAGE_LEVEL('Master Sheet'!F2) (count=1)
  - =IDS_GUARDIAN_ATTACK_COOLDOWN_LEVEL('Master Sheet'!F3) (count=1)
  - =IDS_GUARDIAN_ATTACK_TARGETS_LEVEL('Master Sheet'!F4) (count=1)
  - =LET(
  Targets, DVT_GUARDIAN_STAT("Attack", "Targets", Q5),
  CD, DVT_GUARDIAN_STAT("Attack", "Cooldown", P5),
  Perc, DVT_GUARDIAN_STAT("Attack", "Percentage", O5),
Targets*(Perc/CD)) (count=1)
  - =LET(
  Targets, DVT_GUARDIAN_STAT("Attack", "Targets", Q5),
  CD, DVT_GUARDIAN_STAT("Attack", "Cooldown", P5),
  Perc, DVT_GUARDIAN_STAT("Attack", "Percentage", O5+1),
IF(O5<D$3, Targets*(Perc/CD), "")) (count=1)
  - =LET(
  Targets, DVT_GUARDIAN_STAT("Attack", "Targets", Q5),
  CD, DVT_GUARDIAN_STAT("Attack", "Cooldown", P5+1),
  Perc, DVT_GUARDIAN_STAT("Attack", "Percentage", O5),
IF(P5<D$4, Targets*(Perc/CD), "")) (count=1)
- Preview (first 5 rows × 10 cols):
  - [None, None, None, None, None, None, None, None, None, None]
  - [None, None, None, None, None, None, None, None, None, None]
  - [None, None, 'Percentage', '=COUNTA(DVT_GAR_UG_AT_PER)-1', 'ATTACK PATH', 'v0.27', None, None, None, None]
  - [None, None, 'Cooldown', '=COUNTA(DVT_GAR_UG_AT_COO)-1', None, 'Upgrade', 'Level', 'Cost', 'ROI / Bits', 'Final Bonus']
  - [None, None, 'Targets', '=COUNTA(DVT_GAR_UG_AT_TAR)-1', None, None, None, None, None, None]

### Sheet: Ally Path
- Dimensions: None rows × None cols
- First non-empty header-like row: 3
- Header values (non-empty): ['Recovery Amount', '=COUNTA(DVT_GAR_UG_AL_REC)-1', 'ALLY PATH', 'v0.27', 'LAB PATH UPDATE RUNNING', 'eEcon SIMULATIONS', 'TIME USAGE VS eEcon GAIN', 'LAB PATH UPDATE MATRIX']
- Formula cells: 2628 (scanned 5376 cells)
- Top formulas (up to 10):
  - =COUNTA(DVT_GAR_UG_AL_REC)-1 (count=1)
  - =COUNTA(DVT_GAR_UG_AL_MAX)-1 (count=1)
  - =COUNTA(DVT_GAR_UG_AL_COO)-1 (count=1)
  - =S5 (count=1)
  - =IDS_GUARDIAN_ALLY_RECOVERY_AMOUNT_LEVEL('Master Sheet'!F5) (count=1)
  - =IDS_GUARDIAN_ALLY_MAX_RECOVERY_LEVEL('Master Sheet'!F6) (count=1)
  - =IDS_GUARDIAN_ALLY_COOLDOWN_LEVEL('Master Sheet'!F7) (count=1)
  - =LET(
  Amount, DVT_GUARDIAN_STAT("Ally", "Recovery Amount", O5),
  Max, DVT_GUARDIAN_STAT("Ally", "Max Recovery", P5),
  CD, DVT_GUARDIAN_STAT("Ally", "Cooldown", Q5),
Amount*Max/CD) (count=1)
  - =LET(
  Amount, DVT_GUARDIAN_STAT("Ally", "Recovery Amount", O5+1),
  Max, DVT_GUARDIAN_STAT("Ally", "Max Recovery", P5),
  CD, DVT_GUARDIAN_STAT("Ally", "Cooldown", Q5),
IF(O5<D$3, Amount*Max/CD,)) (count=1)
  - =LET(
  Amount, DVT_GUARDIAN_STAT("Ally", "Recovery Amount", O5),
  Max, DVT_GUARDIAN_STAT("Ally", "Max Recovery", P5+1),
  CD, DVT_GUARDIAN_STAT("Ally", "Cooldown", Q5),
IF(P5<D$4, Amount*Max/CD,)) (count=1)
- Preview (first 5 rows × 10 cols):
  - [None, None, None, None, None, None, None, None, None, None]
  - [None, None, None, None, None, None, None, None, None, None]
  - [None, None, 'Recovery Amount', '=COUNTA(DVT_GAR_UG_AL_REC)-1', 'ALLY PATH', 'v0.27', None, None, None, None]
  - [None, None, 'Max Recovery', '=COUNTA(DVT_GAR_UG_AL_MAX)-1', None, 'Upgrade', 'Level', 'Cost', 'ROI / Bits', 'Final Bonus']
  - [None, None, 'Cooldown', '=COUNTA(DVT_GAR_UG_AL_COO)-1', None, None, None, None, None, None]

### Sheet: Bounty Path
- Dimensions: None rows × None cols
- First non-empty header-like row: 3
- Header values (non-empty): ['Multiplier', '=COUNTA(DVT_GAR_UG_BO_MUL)-1', 'BOUNTY PATH', 'v0.27', 'LAB PATH UPDATE RUNNING', 'eEcon SIMULATIONS', 'TIME USAGE VS eEcon GAIN', 'LAB PATH UPDATE MATRIX']
- Formula cells: 2718 (scanned 5536 cells)
- Top formulas (up to 10):
  - =COUNTA(DVT_GAR_UG_BO_MUL)-1 (count=1)
  - =COUNTA(DVT_GAR_UG_BO_COO)-1 (count=1)
  - =C3 (count=1)
  - =C4 (count=1)
  - =C5 (count=1)
  - =O4 (count=1)
  - =P4 (count=1)
  - =Q4 (count=1)
  - =U4 (count=1)
  - =V4 (count=1)
- Preview (first 5 rows × 10 cols):
  - [None, None, None, None, None, None, None, None, None, None]
  - [None, None, None, None, None, None, None, None, None, None]
  - [None, None, 'Multiplier', '=COUNTA(DVT_GAR_UG_BO_MUL)-1', 'BOUNTY PATH', 'v0.27', None, None, None, None]
  - [None, None, 'Cooldown', '=COUNTA(DVT_GAR_UG_BO_COO)-1', None, 'Upgrade', 'Level', 'Cost', 'ROI / Bits', 'Final Bonus']
  - [None, None, 'Targets', '=COUNTA(DVT_GAR_UG_BO_TAR)-1', None, None, None, None, None, None]

### Sheet: Fetch Path
- Dimensions: None rows × None cols
- First non-empty header-like row: 3
- Header values (non-empty): ['Cooldown', '=COUNTA(DVT_GAR_UG_FE_COO)-1', 'FETCH PATH', 'v0.27', <openpyxl.worksheet.formula.ArrayFormula object at 0x7ff5831a2350>, <openpyxl.worksheet.formula.ArrayFormula object at 0x7ff5831a26b0>, <openpyxl.worksheet.formula.ArrayFormula object at 0x7ff5831a27d0>, <openpyxl.worksheet.formula.ArrayFormula object at 0x7ff5831a1db0>, 'LAB PATH UPDATE RUNNING', 'eEcon SIMULATIONS', 'TIME USAGE VS eEcon GAIN', 'LAB PATH UPDATE MATRIX']
- Formula cells: 3134 (scanned 5661 cells)
- Top formulas (up to 10):
  - =COUNTA(DVT_GAR_UG_FE_COO)-1 (count=1)
  - <openpyxl.worksheet.formula.ArrayFormula object at 0x7ff5831a2290> (count=1)
  - <openpyxl.worksheet.formula.ArrayFormula object at 0x7ff5831a2770> (count=1)
  - <openpyxl.worksheet.formula.ArrayFormula object at 0x7ff5831a25f0> (count=1)
  - <openpyxl.worksheet.formula.ArrayFormula object at 0x7ff5831a1330> (count=1)
  - =COUNTA(DVT_GAR_UG_FE_FIN)-1 (count=1)
  - =COUNTA(DVT_GAR_UG_FE_DOU)-1 (count=1)
  - =Y5 (count=1)
  - =IDS_GUARDIAN_FETCH_COOLDOWN_LEVEL('Master Sheet'!F11) (count=1)
  - =IDS_GUARDIAN_FETCH_FIND_CHANCE_LEVEL('Master Sheet'!F12) (count=1)
- Preview (first 5 rows × 10 cols):
  - [None, None, None, None, None, None, None, None, None, None]
  - [None, None, None, None, None, None, None, None, None, None]
  - [None, None, 'Cooldown', '=COUNTA(DVT_GAR_UG_FE_COO)-1', 'FETCH PATH', 'v0.27', None, None, None, None]
  - [None, None, 'Find Chance', '=COUNTA(DVT_GAR_UG_FE_FIN)-1', None, 'Upgrade', 'Level', 'Cost', 'ROI / Bits', 'Loot / Hour']
  - [None, None, 'Double Find Chance', '=COUNTA(DVT_GAR_UG_FE_DOU)-1', None, None, None, None, None, None]

### Sheet: EXPORT
- Dimensions: None rows × None cols
- First non-empty header-like row: 4
- Header values (non-empty): ['Guardians', 'Attribute', 'Level', 'Bits']
- Formula cells: 72 (scanned 160 cells)
- Top formulas (up to 10):
  - ='Master Sheet'!D18 (count=1)
  - ='Master Sheet'!B2 (count=1)
  - ='Master Sheet'!D2 (count=1)
  - ='Master Sheet'!E2 (count=1)
  - ='Master Sheet'!F2 (count=1)
  - ='Master Sheet'!G2 (count=1)
  - ='Master Sheet'!D3 (count=1)
  - ='Master Sheet'!E3 (count=1)
  - ='Master Sheet'!F3 (count=1)
  - ='Master Sheet'!G3 (count=1)
- Preview (first 5 rows × 10 cols):
  - ['Gv2', None, None, None, None, None, None, None, None, None]
  - [None, 'Bits Spent', None, "='Master Sheet'!D18", None, None, None, None, None, None]
  - [None, None, None, None, None, None, None, None, None, None]
  - [None, 'Guardians', None, 'Attribute', None, 'Level', 'Bits', None, None, None]
  - [None, "='Master Sheet'!B2", None, "='Master Sheet'!D2", "='Master Sheet'!E2", "='Master Sheet'!F2", "='Master Sheet'!G2", None, None, None]
- EXPORT columns (7): ['Gv2', 'Unnamed: 1', 'Unnamed: 2', 'Unnamed: 3', 'Unnamed: 4', 'Unnamed: 5', 'Unnamed: 6']
- EXPORT row count: 18

### Sheet: DVT_Guardians
- Dimensions: None rows × None cols
- First non-empty header-like row: 1
- Header values (non-empty): ['DVT_GAR_UG_AT_PER', 'DVT_GAR_UG_AT_COO', 'DVT_GAR_UG_AT_TAR', 'Attack', 'DVT_GAR_UG_AL_REC', 'DVT_GAR_UG_AL_MAX', 'DVT_GAR_UG_AL_COO', 'Ally', 'DVT_GAR_UG_BO_MUL', 'DVT_GAR_UG_BO_COO', 'DVT_GAR_UG_BO_TAR', 'Bounty', 'DVT_GAR_UG_FE_COO', 'DVT_GAR_UG_FE_FIN', 'DVT_GAR_UG_FE_DOU', 'Fetch', 'DVT_GAR_UG_SU_COO', 'DVT_GAR_UG_SU_DUR', 'DVT_GAR_UG_SU_CAS', 'Summon']
- Formula cells: 890 (scanned 20000 cells - truncated)
- Top formulas (up to 10):
  - =TEXT(F4,"00") & " | " & TEXT(G4*100, "0") & "% | Cost " & H4 & " ⧈ |" & IF(H5="Max", " Maxed", " Next " & H5 & " ⧈") (count=1)
  - =TEXT(F4,"00") & " | " & TEXT(I4, "0") & "s | Cost " & J4 & " ⧈ |" & IF(J5="Max", " Maxed", " Next " & J5 & " ⧈") (count=1)
  - =TEXT(F4,"00") & " | " & TEXT(K4, "0") & " | Cost " & L4 & " ⧈ |" & IF(L5="Max", " Maxed", " Next " & L5 & " ⧈") (count=1)
  - =TEXT(Q4,"00") & " | " & TEXT(R4*100, "0") & "% | Cost " & S4 & " ⧈ |" & IF(S5="Max", " Maxed", " Next " & S5 & " ⧈") (count=1)
  - =TEXT(Q4,"00") & " | " & TEXT(T4, "0.0") & "x | Cost " & U4 & " ⧈ |" & IF(U5="Max", " Maxed", " Next " & U5 & " ⧈") (count=1)
  - =TEXT(Q4,"00") & " | " & TEXT(V4, "0") & "s | Cost " & W4 & " ⧈ |" & IF(W5="Max", " Maxed", " Next " & W5 & " ⧈") (count=1)
  - =TEXT(AB4,"00") & " | " & TEXT(AC4, "0.00") & "x | Cost " & AD4 & " ⧈ |" & IF(AD5="Max", " Maxed", " Next " & AD5 & " ⧈") (count=1)
  - =TEXT(AB4,"00") & " | " & TEXT(AE4, "0") & "s | Cost " & AF4 & " ⧈ |" & IF(AF5="Max", " Maxed", " Next " & AF5 & " ⧈") (count=1)
  - =TEXT(AB4,"00") & " | " & TEXT(AG4, "0") & " | Cost " & AH4 & " ⧈ |" & IF(AH5="Max", " Maxed", " Next " & AH5 & " ⧈") (count=1)
  - =TEXT(AM4,"00") & " | " & TEXT(AN4, "0.0") & "s | Cost " & AO4 & " ⧈ |" & IF(AO5="Max", " Maxed", " Next " & AO5 & " ⧈") (count=1)
- Preview (first 5 rows × 10 cols):
  - [None, None, 'DVT_GAR_UG_AT_PER', 'DVT_GAR_UG_AT_COO', 'DVT_GAR_UG_AT_TAR', None, 'Attack', None, None, None]
  - ['GUARDIANS', 'ATTACK', None, None, None, None, 'Percentage', 'Cost', 'Cooldown', 'Cost']
  - [None, None, None, None, None, None, 'Locked', 0.0, 'Locked', 0.0]
  - [None, None, '=TEXT(F4,"00") & " | " & TEXT(G4*100, "0") & "% | Cost " & H4 & " ⧈ |" & IF(H5="Max", " Maxed", " Next " & H5 & " ⧈")', '=TEXT(F4,"00") & " | " & TEXT(I4, "0") & "s | Cost " & J4 & " ⧈ |" & IF(J5="Max", " Maxed", " Next " & J5 & " ⧈")', '=TEXT(F4,"00") & " | " & TEXT(K4, "0") & " | Cost " & L4 & " ⧈ |" & IF(L5="Max", " Maxed", " Next " & L5 & " ⧈")', 0.0, 0.01, 0.0, 120.0, 0.0]
  - [None, None, '=TEXT(F5,"00") & " | " & TEXT(G5*100, "0") & "% | Cost " & H5 & " ⧈ |" & IF(H6="Max", " Maxed", " Next " & H6 & " ⧈")', '=TEXT(F5,"00") & " | " & TEXT(I5, "0") & "s | Cost " & J5 & " ⧈ |" & IF(J6="Max", " Maxed", " Next " & J6 & " ⧈")', '=TEXT(F5,"00") & " | " & TEXT(K5, "0") & " | Cost " & L5 & " ⧈ |" & IF(L6="Max", " Maxed", " Next " & L6 & " ⧈")', 1.0, 0.02, 25.0, 119.0, 1.0]

### Sheet: Summon Path
- Dimensions: None rows × None cols
- First non-empty header-like row: 3
- Header values (non-empty): ['Cooldown', '=COUNTA(DVT_Guardians!AY4:AY105)-1', 'SUMMON PATH', 'v0.27', 'LAB PATH UPDATE RUNNING', 'eEcon SIMULATIONS', 'TIME USAGE VS eEcon GAIN', 'LAB PATH UPDATE MATRIX']
- Formula cells: 1315 (scanned 2940 cells)
- Top formulas (up to 10):
  - =COUNTA(DVT_Guardians!AY4:AY105)-1 (count=1)
  - =COUNTA(DVT_Guardians!BA4:BA105)-1 (count=1)
  - =COUNTA(DVT_Guardians!BD4:BD105)-1 (count=1)
  - =R5 (count=1)
  - =LEFT('Master Sheet'!F14, 2)+0 (count=1)
  - =LEFT('Master Sheet'!F15, 2)+0 (count=1)
  - =LET(
  CD, DVT_GUARDIAN_STAT("Summon", "Cooldown", O5),
  Dur, DVT_GUARDIAN_STAT("Summon", "Duration", P5),
Dur/CD*2) (count=1)
  - =LET(
  CD, DVT_GUARDIAN_STAT("Summon", "Cooldown", O5+1),
  Dur, DVT_GUARDIAN_STAT("Summon", "Duration", P5),
IF(O5<D$3, Dur/CD*2, "")) (count=1)
  - =LET(
  CD, DVT_GUARDIAN_STAT("Summon", "Cooldown", O5),
  Dur, DVT_GUARDIAN_STAT("Summon", "Duration", P5+1),
IF(P5<D$4, Dur/CD*2, "")) (count=1)
  - =IF(T5="","",(T5/$R5-1)/DVT_GUARDIAN_COST("Summon", W$4, O5+1)) (count=1)
- Preview (first 5 rows × 10 cols):
  - [None, None, None, None, None, None, None, None, None, None]
  - [None, None, None, None, None, None, None, None, None, None]
  - [None, None, 'Cooldown', '=COUNTA(DVT_Guardians!AY4:AY105)-1', 'SUMMON PATH', 'v0.27', None, None, None, None]
  - [None, None, 'Duration', '=COUNTA(DVT_Guardians!BA4:BA105)-1', None, 'Upgrade', 'Level', 'Cost', 'ROI / Bits', 'Enemy / Second']
  - [None, None, None, '=COUNTA(DVT_Guardians!BD4:BD105)-1', None, None, None, None, None, None]

### Sheet: All Chips
- Dimensions: None rows × None cols
- First non-empty header-like row: 1
- Header values (non-empty): ['=SUM(C1:AM1)', '=Sum(C$4:C104)', '=Sum(F$4:F104)', '=Sum(H$4:H104)', '=Sum(J$4:J104)', '=Sum(M$4:M104)', '=Sum(O$4:O104)', '=Sum(Q$4:Q104)', '=Sum(T$4:T104)', '=Sum(V$4:V104)', '=Sum(X$4:X104)', '=Sum(AA$4:AA104)', '=Sum(AC$4:AC104)', '=Sum(AE$4:AE104)']
- Formula cells: 2230 (scanned 4056 cells)
- Top formulas (up to 10):
  - =DVT_GUARDIAN_STAT(S$2,S$3,ROW()-4) (count=100)
  - =DVT_GUARDIAN_COST(S$2,S$3,ROW()-4) (count=100)
  - =DVT_GUARDIAN_STAT(S$2,U$3,ROW()-4) (count=100)
  - =DVT_GUARDIAN_COST(S$2,U$3,ROW()-4) (count=100)
  - =DVT_GUARDIAN_STAT(S$2,W$3,ROW()-4) (count=100)
  - =DVT_GUARDIAN_COST(S$2,W$3,ROW()-4) (count=100)
  - =DVT_GUARDIAN_STAT(E$2,E$3,ROW()-4) (count=91)
  - =DVT_GUARDIAN_COST(E$2,E$3,ROW()-4) (count=91)
  - =DVT_GUARDIAN_STAT(E$2,G$3,ROW()-4) (count=91)
  - =DVT_GUARDIAN_COST(E$2,G$3,ROW()-4) (count=91)
- Preview (first 5 rows × 10 cols):
  - [None, '=SUM(C1:AM1)', '=Sum(C$4:C104)', None, None, '=Sum(F$4:F104)', None, '=Sum(H$4:H104)', None, '=Sum(J$4:J104)']
  - [None, 'Unlock Costs per Slot', None, None, 'Attack', None, None, None, None, None]
  - [None, '# Bots', 'Cost', None, 'Percentage', 'Cost', 'Cooldown', 'Cost', 'Targets', 'Cost']
  - ['GUARDIAN UNLOCKS', 0.0, 0.0, 'ATTACK', '=DVT_GUARDIAN_STAT(E$2,E$3,ROW()-4)', '=DVT_GUARDIAN_COST(E$2,E$3,ROW()-4)', '=DVT_GUARDIAN_STAT(E$2,G$3,ROW()-4)', '=DVT_GUARDIAN_COST(E$2,G$3,ROW()-4)', '=DVT_GUARDIAN_STAT(E$2,I$3,ROW()-4)', '=DVT_GUARDIAN_COST(E$2,I$3,ROW()-4)']
  - [None, 1.0, 0.0, None, '=DVT_GUARDIAN_STAT(E$2,E$3,ROW()-4)', '=DVT_GUARDIAN_COST(E$2,E$3,ROW()-4)', '=DVT_GUARDIAN_STAT(E$2,G$3,ROW()-4)', '=DVT_GUARDIAN_COST(E$2,G$3,ROW()-4)', '=DVT_GUARDIAN_STAT(E$2,I$3,ROW()-4)', '=DVT_GUARDIAN_COST(E$2,I$3,ROW()-4)']

## Copy of Laboratory v2.3.2.xlsx
- Size: 1198369 bytes
- Sheets: Home Page, IDS, _IDS, Master Sheet, Lab Calculator, Lab Planner, DVT_Laboratory, DVT_Laboratory2, Tier List, Lab Boost Calculator, Short Lab Path, Interactive Thorns, ELS BC Reduction, Elites Spawncap, EXPORT

### Sheet: Home Page
- Dimensions: None rows × None cols
- First non-empty header-like row: 4
- Header values (non-empty): ['=HYPERLINK("https://docs.google.com/spreadsheets/d/165-JujisYPpKi3RWew9O5gptDJ6rgr-71BbyoQafoaU/copy", "Laboratory Initial Link")', 'Sheet Tab', 'Creator', 'Main Contributor', 'Helpers']
- Formula cells: 7 (scanned 533 cells)
- Top formulas (up to 10):
  - =HYPERLINK("https://docs.google.com/spreadsheets/d/165-JujisYPpKi3RWew9O5gptDJ6rgr-71BbyoQafoaU/copy", "Laboratory Initial Link") (count=1)
  - =IFERROR(__xludf.DUMMYFUNCTION("IMPORTRANGE(""165-JujisYPpKi3RWew9O5gptDJ6rgr-71BbyoQafoaU"", ""'Home Page'!B12:C13"")"),"v2.3.2") (count=1)
  - =IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),"fix: Lab Speed Relic formula") (count=1)
  - =IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),"v2.3.1") (count=1)
  - =IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),"fix: Minor tweaks to Lab Boost Calculator") (count=1)
  - =IFERROR(__xludf.DUMMYFUNCTION("IMPORTRANGE(""1eCPPuQOE3Pyh8HhnApEMK3RFIutkUjWd61ppVImwWk8"", ""_Giveaway_summary!A1:A2"")"),"⚠️ 2 Giveaway(s) running - 2 Feb | 5 Feb") (count=1)
  - =IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),"Giveaway Details") (count=1)
- Preview (first 5 rows × 10 cols):
  - [None, None, None, None, None, None, None, None, None, None]
  - [None, 'Laboratory', None, None, None, None, None, None, None, None]
  - [None, None, None, None, None, None, None, None, None, None]
  - [None, '=HYPERLINK("https://docs.google.com/spreadsheets/d/165-JujisYPpKi3RWew9O5gptDJ6rgr-71BbyoQafoaU/copy", "Laboratory Initial Link")', None, None, None, None, 'Sheet Tab', 'Creator', 'Main Contributor', 'Helpers']
  - [None, None, None, None, None, None, None, None, None, None]

### Sheet: IDS
- Dimensions: None rows × None cols
- First non-empty header-like row: 6
- Header values (non-empty): ["IDS Master's ID       ➡️", '18XbHJtHzu8tjqnP_9JcsZFA6jIwjOKRYmzBzOYBMv2I', '=IFERROR(__xludf.DUMMYFUNCTION("IFERROR(C6.url, IFS(LEFT(C6,8)=""https://"", C6, LEN(C6)=44, ""https://docs.google.com/spreadsheets/d/"" & C6 & ""/edit"", TRUE, C6))"),"https://docs.google.com/spreadsheets/d/18XbHJtHzu8tjqnP_9JcsZFA6jIwjOKRYmzBzOYBMv2I/edit")', '=IFERROR(__xludf.DUMMYFUNCTION("IF(D6<>"""", IF(IMPORTRANGE(D6,""EXPORT!A1"") = F6, ""✅"", ""Wrong ID or Version""), """")"),"✅")', 'v2']
- Formula cells: 4 (scanned 258 cells)
- Top formulas (up to 10):
  - =IFERROR(__xludf.DUMMYFUNCTION("IFERROR(C6.url, IFS(LEFT(C6,8)=""https://"", C6, LEN(C6)=44, ""https://docs.google.com/spreadsheets/d/"" & C6 & ""/edit"", TRUE, C6))"),"https://docs.google.com/spreadsheets/d/18XbHJtHzu8tjqnP_9JcsZFA6jIwjOKRYmzBzOYBMv2I/edit") (count=1)
  - =IFERROR(__xludf.DUMMYFUNCTION("IF(D6<>"""", IF(IMPORTRANGE(D6,""EXPORT!A1"") = F6, ""✅"", ""Wrong ID or Version""), """")"),"✅") (count=1)
  - =HYPERLINK("https://docs.google.com/spreadsheets/d/1osjoqKmMwtOWs7Up3e21-3ofN1RHOjsgKV6y3dc6rgE/copy", "1️⃣ Copy Me") (count=1)
  - =IFS(
  ISERROR(E6), "3️⃣ Click on #REF! and then AUTHORISE ↗",
  E6="", "2️⃣ Please input your IDS Master's ID here ⤴️",
  E6="✅", HYPERLINK(D6, "Go to my IDS Master Sheet"),
  TRUE, "") (count=1)
- Preview (first 5 rows × 10 cols):
  - [None, None, None, None, None, None, None, None, None, None]
  - [None, 'The IDS System', None, None, None, None, None, None, 'Looking for the Import script ? Just run it as you were doing it before, but from IDS Master.\nIt will let you import every new versions at once!', None]
  - [None, None, None, None, None, None, None, None, None, None]
  - [None, 'This Sheet ID is :', '1yLi6Ni4nZr0Wfct7MmbyNRRi5v6fR62t0kdI-g8NeNo', None, None, None, None, None, None, None]
  - [None, None, None, None, None, None, None, None, None, None]

### Sheet: _IDS
- Dimensions: None rows × None cols
- First non-empty header-like row: 1
- Header values (non-empty): ['=IFERROR(__xludf.DUMMYFUNCTION("IMPORTRANGE(IF(IDS!E6=""✅"", IDS!D6, ""1osjoqKmMwtOWs7Up3e21-3ofN1RHOjsgKV6y3dc6rgE""), ""_IDS!A1:CE212"")"),"Labs")', '=IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),"https://docs.google.com/spreadsheets/d/1yLi6Ni4nZr0Wfct7MmbyNRRi5v6fR62t0kdI-g8NeNo/edit")', '=IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),"✅")', '=IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),"v2.3.2")', '=IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),"WS")', '=IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),"https://docs.google.com/spreadsheets/d/1462mmIeTEmChEYwwpDWacv611QCRW9n-Dvz8oyOQ798/edit")', '=IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),"✅")', '=IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),"v2.2.8")', '=IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),"WS+")', '=IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),"UWs")', '=IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),"https://docs.google.com/spreadsheets/d/1aLEWX2qblJJt96I6QduS_Fp2DjMO6rNToPrUBWGI5BU/edit")', '=IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),"✅")', '=IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),"v2.1.2")', '=IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),"Cards")', '=IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),"https://docs.google.com/spreadsheets/d/1HMQwNLTvcw7aXmjjL7cXmZSdjAF_62ehWpwDIdjqEGs/edit")', '=IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),"✅")', '=IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),"Cards Presets")', '=IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),"v2.2.3")', '=IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),"Relics")', '=IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),"https://docs.google.com/spreadsheets/d/1jtZ_RhMszIY0NzPm-kNhYg_w5D8WDm9tXSJatvVpWDU/edit")', '=IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),"✅")', '=IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),"Vault")', '=IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),"")', '=IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),"Bots")', '=IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),"https://docs.google.com/spreadsheets/d/1gopHNYu4SgI0UbRvscCV4_C1gct7FXr5GBBcjCzCxC0/edit")', '=IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),"✅")', '=IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),"v2.2")', '=IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),"Themes & Songs")', '=IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),"https://docs.google.com/spreadsheets/d/1umYUbdc7TGYJhqFv662Yol9PGzfECdpLYxl4ElV6UwQ/edit")', '=IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),"✅")', '=IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),"Modules")', '=IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),"https://docs.google.com/spreadsheets/d/1mz0hSpsng0Kzlz8xk0VEyRgaE62Gzj5kNLu3Vp-4gGE/edit")', '=IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),"✅")', '=IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),"v5.12")', '=IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),"Guardians")', '=IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),"https://docs.google.com/spreadsheets/d/19vecjglXSr9t51C6vJy-lMGk1xH4h52ytBr-uyKxLcM/edit")', '=IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),"✅")', '=IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),"v2.2.5")', '=IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),"Player & Stuff")', '=IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),"https://docs.google.com/spreadsheets/d/1fjJxEFt9ZZ5og_q7xHZuyRTf3p_OOUNwCXVV6VtGof0/edit")', '=IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),"✅")', '=IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),"v3.5.2")']
- Formula cells: 2561 (scanned 20000 cells - truncated)
- Top formulas (up to 10):
  - =IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),"") (count=186)
  - =IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),0.0) (count=173)
  - =IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),99.0) (count=59)
  - =IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),FALSE) (count=55)
  - =IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),20.0) (count=50)
  - =IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),30.0) (count=49)
  - =IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),7.0) (count=46)
  - =IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),TRUE) (count=45)
  - =IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),1.0) (count=45)
  - =IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),"Stat") (count=33)
- Preview (first 5 rows × 10 cols):
  - ['=IFERROR(__xludf.DUMMYFUNCTION("IMPORTRANGE(IF(IDS!E6=""✅"", IDS!D6, ""1osjoqKmMwtOWs7Up3e21-3ofN1RHOjsgKV6y3dc6rgE""), ""_IDS!A1:CE212"")"),"Labs")', '=IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),"https://docs.google.com/spreadsheets/d/1yLi6Ni4nZr0Wfct7MmbyNRRi5v6fR62t0kdI-g8NeNo/edit")', '=IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),"✅")', '=IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),"v2.3.2")', '=IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),"WS")', '=IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),"https://docs.google.com/spreadsheets/d/1462mmIeTEmChEYwwpDWacv611QCRW9n-Dvz8oyOQ798/edit")', '=IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),"✅")', '=IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),"v2.2.8")', None, None]
  - ['=IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),"Game Speed")', '=IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),7.0)', '=IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),7.0)', '=IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),7.0)', '=IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),"U")', '=IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),"Workshop Upgrade")', '=IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),"Farming")', None, '=IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),"Tourney")', None]
  - ['=IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),"Starting Cash")', '=IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),6.0)', None, '=IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),99.0)', None, None, '=IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),"¢ Level")', '=IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),"$ Level")', '=IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),"¢ Level")', '=IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),"$ Level")']
  - ['=IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),"Workshop Attack Discount")', '=IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),16.0)', None, '=IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),99.0)', None, '=IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),"Damage")', '=IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),5750.0)', '=IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),6000.0)', '=IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),5750.0)', '=IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),6000.0)']
  - ['=IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),"Workshop Defense Discount")', '=IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),19.0)', None, '=IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),99.0)', None, '=IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),"Attack Speed")', '=IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),99.0)', '=IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),99.0)', '=IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),99.0)', '=IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),99.0)']

### Sheet: Master Sheet
- Dimensions: None rows × None cols
- First non-empty header-like row: 1
- Header values (non-empty): ['Labs', 'Level', 'Target', 'Max', 'Labs', 'Level', 'Target', 'Max', 'Labs', 'Level', 'Target', 'Max', 'Labs', 'Level', 'Target', 'Max', 'Labs', 'Level', 'Target', 'Max', 'Labs', 'Level', 'Target', 'Max', 'Labs', 'Level', 'Target', 'Max', 'Labs', 'Level', 'Target', 'Max', 'Labs', 'Level', 'Target', 'Max', 'Labs', 'Level', 'Target', 'Max', 'Labs', 'Level', 'Target', 'Max', 'Workshop Upgrade', '¢ Level', '$ Level', 'Max', 'Card Name', 'Level', 'Mastery']
- Formula cells: 264 (scanned 2795 cells)
- Top formulas (up to 10):
  - =COUNTA(OFFSET(DVT_Laboratory!$B$3, 0, MATCH("Card Mastery",DVT_Laboratory!$B$1:BM$1, 0)-1, 100, 1)) (count=31)
  - ="("&ROUND(C43/E43*100,0)&"%)" (count=1)
  - =COUNTA(OFFSET(DVT_Laboratory!$B$3, 0, MATCH(B2,DVT_Laboratory!$B$1:BM$1, 0)-1, 100, 1)) (count=1)
  - ="("&ROUND(H43/J43*100,0)&"%)" (count=1)
  - =COUNTA(OFFSET(DVT_Laboratory!$B$3, 0, MATCH(G2,DVT_Laboratory!$B$1:BM$1, 0)-1, 100, 1)) (count=1)
  - ="("&ROUND(M43/O43*100,0)&"%)" (count=1)
  - =COUNTA(OFFSET(DVT_Laboratory!$B$3, 0, MATCH(L2,DVT_Laboratory!$B$1:BM$1, 0)-1, 100, 1)) (count=1)
  - ="("&ROUND(R43/T43*100,0)&"%)" (count=1)
  - =COUNTA(OFFSET(DVT_Laboratory!$B$3, 0, MATCH(Q2,DVT_Laboratory!$B$1:BM$1, 0)-1, 100, 1)) (count=1)
  - ="("&ROUND(W43/Y43*100,0)&"%)" (count=1)
- Preview (first 5 rows × 10 cols):
  - [None, 'Labs', 'Level', 'Target', 'Max', None, 'Labs', 'Level', 'Target', 'Max']
  - ['="("&ROUND(C43/E43*100,0)&"%)"', 'Game Speed', 7.0, 7.0, '=COUNTA(OFFSET(DVT_Laboratory!$B$3, 0, MATCH(B2,DVT_Laboratory!$B$1:BM$1, 0)-1, 100, 1))', '="("&ROUND(H43/J43*100,0)&"%)"', 'Damage', 69.0, None, '=COUNTA(OFFSET(DVT_Laboratory!$B$3, 0, MATCH(G2,DVT_Laboratory!$B$1:BM$1, 0)-1, 100, 1))']
  - [None, 'Starting Cash', 6.0, None, '=COUNTA(OFFSET(DVT_Laboratory!$B$3, 0, MATCH(B3,DVT_Laboratory!$B$1:BM$1, 0)-1, 100, 1))', None, 'Attack Speed', 63.0, None, '=COUNTA(OFFSET(DVT_Laboratory!$B$3, 0, MATCH(G3,DVT_Laboratory!$B$1:BM$1, 0)-1, 100, 1))']
  - [None, 'Workshop Attack Discount', 16.0, None, '=COUNTA(OFFSET(DVT_Laboratory!$B$3, 0, MATCH(B4,DVT_Laboratory!$B$1:BM$1, 0)-1, 100, 1))', None, 'Critical Factor', 76.0, None, '=COUNTA(OFFSET(DVT_Laboratory!$B$3, 0, MATCH(G4,DVT_Laboratory!$B$1:BM$1, 0)-1, 100, 1))']
  - ['MAIN RESEARCHES', 'Workshop Defense Discount', 19.0, None, '=COUNTA(OFFSET(DVT_Laboratory!$B$3, 0, MATCH(B5,DVT_Laboratory!$B$1:BM$1, 0)-1, 100, 1))', 'ATTACK', 'Range', 33.0, None, '=COUNTA(OFFSET(DVT_Laboratory!$B$3, 0, MATCH(G5,DVT_Laboratory!$B$1:BM$1, 0)-1, 100, 1))']

### Sheet: Lab Calculator
- Dimensions: None rows × None cols
- First non-empty header-like row: 1
- Header values (non-empty): ['Apply Boost to :', 'All', 'Hide Maxed Labs', 'None', 'Next level', 'Next level +1', 'Max Level']
- Formula cells: 4220 (scanned 4686 cells)
- Top formulas (up to 10):
  - =IF(B$2="x 1.0", "", B$2) (count=211)
  - =VLOOKUP($A3,MS_Labs_Array,2,FALSE) (count=1)
  - =VLOOKUP($A3,MS_Labs_Array,4,FALSE) (count=1)
  - =IF(OR($C3=$D3,$C3="Max"),"Max Level",LABDURATION_SINGLE_ADJUSTED(IF(ISNUMBER(SEARCH("Mastery",A3)),"Card Mastery",A3),C3+1)/IF(B3<>"", RIGHT(B3, 3),1)) (count=1)
  - =IF(ISNUMBER(F3), FORMAT_TIME(F3), F3) (count=1)
  - =IF(OR($C3=$D3,$C3="Max"),"Max Level",LABCOST_SINGLE_ADJUSTED(IF(ISNUMBER(SEARCH("Mastery",A3)),"Card Mastery",A3),C3)) (count=1)
  - =IF(OR($C3+1=$D3,$C3="Max"),"Max Level",LABCOST_SINGLE_ADJUSTED(IF(ISNUMBER(SEARCH("Mastery",A3)),"Card Mastery",A3),C3+1)) (count=1)
  - =IF(ISNUMBER(H3), FORMAT_NUMBER(H3), H3) (count=1)
  - =IF(ISNUMBER(I3), FORMAT_NUMBER(ROUND(I3/F3/24, 2))&"/h", ) (count=1)
  - =IF(OR($C3=$D3,$C3="Max"),"Max Level",TIME_TO_RUSH_GEMS(LABDURATION_SINGLE_ADJUSTED(A3,C3+1))) (count=1)
- Preview (first 5 rows × 10 cols):
  - ['Apply Boost to :', 'All', 'Hide Maxed Labs', None, 'None', 'Next level', None, None, None, None]
  - ['Labs', 'x 1.0', 'Level', 'Max level', 'Unlocked', 'Duration', None, 'Coins', None, None]
  - ['Game Speed', '=IF(B$2="x 1.0", "", B$2)', '=VLOOKUP($A3,MS_Labs_Array,2,FALSE)', '=VLOOKUP($A3,MS_Labs_Array,4,FALSE)', None, '=IF(OR($C3=$D3,$C3="Max"),"Max Level",LABDURATION_SINGLE_ADJUSTED(IF(ISNUMBER(SEARCH("Mastery",A3)),"Card Mastery",A3),C3+1)/IF(B3<>"", RIGHT(B3, 3),1))', '=IF(ISNUMBER(F3), FORMAT_TIME(F3), F3)', '=IF(OR($C3=$D3,$C3="Max"),"Max Level",LABCOST_SINGLE_ADJUSTED(IF(ISNUMBER(SEARCH("Mastery",A3)),"Card Mastery",A3),C3))', '=IF(OR($C3+1=$D3,$C3="Max"),"Max Level",LABCOST_SINGLE_ADJUSTED(IF(ISNUMBER(SEARCH("Mastery",A3)),"Card Mastery",A3),C3+1))', '=IF(ISNUMBER(H3), FORMAT_NUMBER(H3), H3)']
  - ['Starting Cash', '=IF(B$2="x 1.0", "", B$2)', '=VLOOKUP($A4,MS_Labs_Array,2,FALSE)', '=VLOOKUP($A4,MS_Labs_Array,4,FALSE)', None, '=IF(OR($C4=$D4,$C4="Max"),"Max Level",LABDURATION_SINGLE_ADJUSTED(IF(ISNUMBER(SEARCH("Mastery",A4)),"Card Mastery",A4),C4+1)/IF(B4<>"", RIGHT(B4, 3),1))', '=IF(ISNUMBER(F4), FORMAT_TIME(F4), F4)', '=IF(OR($C4=$D4,$C4="Max"),"Max Level",LABCOST_SINGLE_ADJUSTED(IF(ISNUMBER(SEARCH("Mastery",A4)),"Card Mastery",A4),C4))', '=IF(OR($C4+1=$D4,$C4="Max"),"Max Level",LABCOST_SINGLE_ADJUSTED(IF(ISNUMBER(SEARCH("Mastery",A4)),"Card Mastery",A4),C4+1))', '=IF(ISNUMBER(H4), FORMAT_NUMBER(H4), H4)']
  - ['Workshop Attack Discount', '=IF(B$2="x 1.0", "", B$2)', '=VLOOKUP($A5,MS_Labs_Array,2,FALSE)', '=VLOOKUP($A5,MS_Labs_Array,4,FALSE)', 'T2 40', '=IF(OR($C5=$D5,$C5="Max"),"Max Level",LABDURATION_SINGLE_ADJUSTED(IF(ISNUMBER(SEARCH("Mastery",A5)),"Card Mastery",A5),C5+1)/IF(B5<>"", RIGHT(B5, 3),1))', '=IF(ISNUMBER(F5), FORMAT_TIME(F5), F5)', '=IF(OR($C5=$D5,$C5="Max"),"Max Level",LABCOST_SINGLE_ADJUSTED(IF(ISNUMBER(SEARCH("Mastery",A5)),"Card Mastery",A5),C5))', '=IF(OR($C5+1=$D5,$C5="Max"),"Max Level",LABCOST_SINGLE_ADJUSTED(IF(ISNUMBER(SEARCH("Mastery",A5)),"Card Mastery",A5),C5+1))', '=IF(ISNUMBER(H5), FORMAT_NUMBER(H5), H5)']

### Sheet: Lab Planner
- Dimensions: None rows × None cols
- First non-empty header-like row: 1
- Header values (non-empty): ['v0.5.9 by JayCee101', 'Autofill', 'Coins', 'Duration', 'Autofill', 'Coins', 'Duration', 'Autofill', 'Coins', 'Duration', 'Boosts', '#e6b8af', 'Shown Labs', 'Lab Name', 'Level', 'Target', 'Max', 'Lab Slot Calcs']
- Formula cells: 729 (scanned 20000 cells - truncated)
- Top formulas (up to 10):
  - <openpyxl.worksheet.formula.ArrayFormula object at 0x7ff5831c9bd0> (count=1)
  - <openpyxl.worksheet.formula.ArrayFormula object at 0x7ff5831c91e0> (count=1)
  - <openpyxl.worksheet.formula.ArrayFormula object at 0x7ff5831c9f60> (count=1)
  - =IFERROR(__xludf.DUMMYFUNCTION("QUERY(AD2:AG246, SWITCH(V40,
    """", ""Select Col1"",
    ""Show All"", ""Select Col1"",
    ""Completed"", ""Select Col1 where Col2 != Col4"",
    ""Completed & Target"", ""Select Col1 where Col2 != Col3 and Col2 != Col4""))  "),"Amp Bot - Cooldown") (count=1)
  - <openpyxl.worksheet.formula.ArrayFormula object at 0x7ff5831c9ea0> (count=1)
  - =IFERROR(SEQUENCE(1, VALUE(VLOOKUP(E5, AD:AG, 4, false)) - VALUE(VLOOKUP(E5, AD:AG, 2, false)), VLOOKUP(E5, AD:AG, 2, false)),"") (count=1)
  - =FORMAT_NUMBER(SUM(H5:H24)) (count=1)
  - =IFS(
OR(SUM(I$5:I$25) >= 1, SUM(I$5:I$25) = 0),
    ROUND(SUM(I$5:I$25), 1) & " Days",
    SUM(I$5:I$25) < 1,
        ROUNDDOWN(SUM(I$5:I$25)*24, 2) & " Hours")    (count=1)
  - =FORMAT_NUMBER(SUM(P5:P24)) (count=1)
  - =IFS(
OR(SUM(Q$5:Q$25) >= 1, SUM(Q$5:Q$25) = 0),
    ROUND(SUM(Q$5:Q$25), 1) & " Days",
    SUM(Q$5:Q$25) < 1,
        ROUNDDOWN(SUM(Q$5:Q$25)*24, 2) & " Hours")    (count=1)
- Preview (first 5 rows × 10 cols):
  - ['v0.5.9 by JayCee101', 'Autofill', None, None, None, None, None, 'Coins', 'Duration', 'Autofill']
  - [None, <openpyxl.worksheet.formula.ArrayFormula object at 0x7ff5831a06a0>, 'Lab One', None, None, '4x Boost', None, None, None, <openpyxl.worksheet.formula.ArrayFormula object at 0x7ff5831a0730>]
  - [None, None, None, None, None, '=FORMAT_NUMBER(SUM(H5:H24))', '=IFS(\nOR(SUM(I$5:I$25) >= 1, SUM(I$5:I$25) = 0),\n    ROUND(SUM(I$5:I$25), 1) & " Days",\n    SUM(I$5:I$25) < 1,\n        ROUNDDOWN(SUM(I$5:I$25)*24, 2) & " Hours")', None, None, None]
  - [None, <openpyxl.worksheet.formula.ArrayFormula object at 0x7ff5831a07c0>, 'Start', 'End', None, None, None, None, None, <openpyxl.worksheet.formula.ArrayFormula object at 0x7ff5831a0610>]
  - [None, '=IF(E5 = "", "", {"Lab Levels", VLOOKUP(E5, $AD:$AG, 2, FALSE), IF(OR(VLOOKUP(E5, $AD:$AG, 3, FALSE) = "", $W$38 = "Max"), VLOOKUP(E5, $AD:$AG, 4, FALSE), VLOOKUP(E5, $AD:$AG, 3, FALSE))})', 4.0, 5.0, 'Shatter Shards', '=IFERROR(__xludf.DUMMYFUNCTION("IFERROR(IF(H5 = """", """",\n    SWITCH($W$37,\n        ""Total"", "" "" & FORMAT_NUMBER(H5),\n        ""Daily"", LET(Lab_name, IF(REGEXMATCH(E5, ""Mastery""), ""Card Mastery"", E5),\n            Level, IF(ISBETWEEN(C5, VLOOKUP(E5, $AD:$AG, 2, FALSE), VLOOKUP"&"(E5, $AD:$AG, 4, FALSE), TRUE, FALSE), C5, VLOOKUP(E5, $AD:$AG, 2, FALSE)),\n            IF(LABCOST_SINGLE_ADJUSTED(Lab_name, Level + 1) = 0, ""0 (Max)"",\n            "" "" & FORMAT_NUMBER(            \n                    LABCOST_SINGLE_ADJUSTED(Lab_name, "&"Level + 1) / \n                    (LABDURATION_SINGLE_ADJUSTED(Lab_name, Level + 1) /\n                    (1 * REGEXEXTRACT(F$2, ""[\\d.-]+"")))))),\n        ""Gem Rush"", LET(\n            Labspeed, IF(E5=""Labs Speed"", 1+\'Master Sheet\'!$BK$5, LAB_SPEED_TO"&"TAL()),\n            Start_Level, IF(C5 = """",\n                VLOOKUP(E5, $AD:$AG, 2, false),\n                IF(ISBETWEEN(C5, VALUE(VLOOKUP(E5, $AD:$AG, 2, false)), VALUE(VLOOKUP(E5, $AD:$AG, 4, false))), C5, """")),\n            End_Level, IF(OR(D5 = """&""", NOT(ISBETWEEN(D5, VALUE(VLOOKUP(E5, $AD:$AG, 2, false)), VALUE(VLOOKUP(E5, $AD:$AG, 4, false)),0,1))),\n                SWITCH($W$38,\n                    ""Max"", VLOOKUP(E5, $AD:$AG, 4, false),\n                    ""Target"", IF(VLOOKUP(E5, $AD:$AG, 3"&", false) <> """", VLOOKUP(E5, $AD:$AG, 3, false), VLOOKUP(E5, $AD:$AG, 4, false))),\n                    D5),\n            SUM(ARRAYFORMULA(TIME_TO_RUSH_GEMS( OFFSET(DVT_Laboratory!$A$3, Start_Level , IF(ISNUMBER(SEARCH(""mastery"", E5)), MATCH(""Card Maste"&"ry"", DVT_Laboratory!$A$1:$LO$1, 0), MATCH(E5, DVT_Laboratory!$A$1:$LO$1, 0)) - 1, End_Level - Start_Level, 1) / Labspeed)))))))")," 1.03 q")', '=IFERROR(SWITCH(I5,\n"", "",\n"MAX Level", "   MAX Level",\n"At Target", "   At Target",\n"Levels Error!", " Check Levels",\n" " & SWITCH($V$41, "Show Time", FORMAT_TIME(I5), "Show Date", TEXT(NOW()+I5,"dd/mm/yy hh:mm"), "Show Running Date", TEXT(NOW()+SUM(I$5:I5),"dd/mm/yy hh:mm"))),"")', '=IFERROR(__xludf.DUMMYFUNCTION("IFS(E5 = """", """", \n    VLOOKUP(E5, $AD:$AG, 2, false) = VLOOKUP(E5, $AD:$AG, 4, false), ""MAX Level"",\n    AND(VLOOKUP(E5, $AD:$AG, 3, false) <> """", VLOOKUP(E5, $AD:$AG, 2, false) = VLOOKUP(E5, $AD:$AG, 3, false)), ""At Target"",\n    TRUE,\n    IFERRO"&"R(LET(Start_Level, IF(C5 = """",\n            VLOOKUP(E5, $AD:$AG, 2, false),\n            IF(ISBETWEEN(C5, VALUE(VLOOKUP(E5, $AD:$AG, 2, false)), VALUE(VLOOKUP(E5, $AD:$AG, 4, false))), C5, """")),\n        End_Level, IF(OR(D5 = """", NOT(ISBETWEEN(D5, VALU"&"E(VLOOKUP(E5, $AD:$AG, 2, false)), VALUE(VLOOKUP(E5, $AD:$AG, 4, false)),0,1))),\n            SWITCH($W$38,\n                ""Max"", VLOOKUP(E5, $AD:$AG, 4, false),\n                ""Target"", IF(VLOOKUP(E5, $AD:$AG, 3, false) <> """", VLOOKUP(E5, $AD:$AG,"&" 3, false), VLOOKUP(E5, $AD:$AG, 4, false))),\n            D5),\n        SUM(OFFSET(DVT_Laboratory!$A$3, Start_Level , IF(ISNUMBER(SEARCH(""mastery"", E5)), MATCH(""Card Mastery"", DVT_Laboratory!$A$1:$MY$1, 0), MATCH(E5, DVT_Laboratory!$A$1:$MY$1, 0)), End"&"_Level - Start_Level, 1)) * (1-LAB_COIN_DISCOUNT())), ""Levels Error!""))"),1.02935E15)', '=IFERROR(__xludf.DUMMYFUNCTION("IFS(E5 = """", """", \n    VLOOKUP(E5, $AD:$AG, 2, false) = VLOOKUP(E5, $AD:$AG, 4, false), ""MAX Level"",\n    AND(VLOOKUP(E5, $AD:$AG, 3, false) <> """", VLOOKUP(E5, $AD:$AG, 2, false) = VLOOKUP(E5, $AD:$AG, 3, false)), ""At Target"",\n    TRUE,\n    IFERRO"&"R(LET(\n        Labspeed, IF(E5=""Labs Speed"", 1+\'Master Sheet\'!$BK$5, LAB_SPEED_TOTAL()),\n        Start_Level, IF(C5 = """",\n            VLOOKUP(E5, $AD:$AG, 2, false),\n            IF(ISBETWEEN(C5, VALUE(VLOOKUP(E5, $AD:$AG, 2, false)), VALUE(VLOOKUP(E5,"&" $AD:$AG, 4, false))), C5, """")),\n        End_Level, IF(OR(D5 = """", NOT(ISBETWEEN(D5, VALUE(VLOOKUP(E5, $AD:$AG, 2, false)), VALUE(VLOOKUP(E5, $AD:$AG, 4, false)),0,1))),\n            SWITCH($W$38,\n                ""Max"", VLOOKUP(E5, $AD:$AG, 4, false)"&",\n                ""Target"", IF(VLOOKUP(E5, $AD:$AG, 3, false) <> """", VLOOKUP(E5, $AD:$AG, 3, false), VLOOKUP(E5, $AD:$AG, 4, false))),\n            D5),\n        SUM(OFFSET(DVT_Laboratory!$A$3, Start_Level , IF(ISNUMBER(SEARCH(""mastery"", E5)), MATCH("&"""Card Mastery"", DVT_Laboratory!$A$1:$MY$1, 0), MATCH(E5, DVT_Laboratory!$A$1:$MY$1, 0)) - 1, End_Level - Start_Level, 1)) /\n                (1 * REGEXEXTRACT(F$2, ""[\\d.-]+"")) /\n                Labspeed), ""Levels Error!""))"),36.9190056860052)', '=IF(M5 = "", "", {"Lab Levels", VLOOKUP(M5, $AD:$AG, 2, FALSE), IF(OR(VLOOKUP(M5, $AD:$AG, 3, FALSE) = "", $W$38 = "Max"), VLOOKUP(M5, $AD:$AG, 4, FALSE), VLOOKUP(M5, $AD:$AG, 3, FALSE))})']

### Sheet: DVT_Laboratory
- Dimensions: None rows × None cols
- First non-empty header-like row: 1
- Header values (non-empty): ['Game Speed', 'Starting Cash', 'Workshop Attack Discount', 'Workshop Defense Discount', 'Workshop Utility Discount', 'Labs Coin Discount', 'Labs Speed', 'Buy Multiplier', 'More Round Stats', 'Target Priority', 'Card Presets', 'Workshop Respec', 'Reroll Daily Mission', 'Workshop Enhancements', 'Enhancement Attack - Coin Discount', 'Enhancement Defense - Coin Discount', 'Enhancement Utility - Coin Discount', 'Damage', 'Attack Speed', 'Critical Factor', 'Range', 'Damage / Meter', 'Super Crit Chance', 'Super Crit Multi', 'Max Rend Armor Multiplier', 'Light Speed Shots', 'Health', 'Health Regen', 'Defense Absolute', 'Defense %', 'Orbs Speed', 'Land Mine Damage', 'Land Mine Decay', 'Shockwave Size', 'Orb Boss Hit', 'Wall Health', 'Wall Rebuild', 'Wall Regen', 'Wall Thorns', 'Wall Invincibility', 'Wall Fortification', 'Garlic Thorns', 'Cash Bonus', 'Cash / Wave', 'Coins / Kill Bonus', 'Coins / Wave', 'Interest', 'Max Interest', 'Package After Boss', 'Recovery Package Amount', 'Recovery Package Max', 'Recovery Package Chance', 'Enemy Attack Level Skip', 'Enemy Health Level Skip', 'Missile Despawn Time', 'Missiles Explosion', 'Missile Radius', 'Chrono Field Duration', 'Chrono Field Damage Reduction', 'Chrono Field Reduction %', 'Swamp Radius', 'Swamp Stun', 'Swamp Stun Chance', 'Swamp Stun Time', 'Golden Tower Bonus', 'Golden Tower Duration', 'Chain Lightning Shock', 'Shock Chance', 'Shock Multiplier', 'Death Wave Health', 'Death Wave Coin bonus', 'Inner Mine Blast Radius', 'Inner Mine Rotation Speed', 'Chrono Field Range', 'Missile Amplifier', 'Missile Barrage', 'Missile Barrage Quantity', 'Inner Mine Stun', 'Black Hole Damage', 'Extra Black Hole', 'Black Hole Coin Bonus', 'Spotlight Coin Bonus', 'Spotlight Missiles', 'Black Hole Disable Ranged Enemies', 'Recharge Missile Barrage', 'Swamp Rend', 'Swamp Rend - Additional Enemies', 'Chain Thunder', 'Lightning Amplifier - Scatter', 'Death Wave Cells Bonus', 'Death Wave Damage Amplifier', 'Death Wave Armor Stripping', 'Inner Land Mine - Chrono Jump', 'Second Wind Blast', 'Double Death Ray', 'Extra Orb Adjuster', 'Extra Extra Orbs', 'Energy Shield Extra Hit', 'Super Tower Bonus', 'Recharge Second Wind', 'Recharge Demon Mode', 'Recharge Nuke', 'Card Mastery', 'Unlock Perks', 'Waves Required', 'Auto Pick Perks', 'Standard Perks Bonus', 'Perk Option Quantity', 'First Perk Choice', 'Ban Perks', 'Improve Trade-off Perks', 'Auto Pick Ranking', 'Flame Bot - Cooldown', 'Thunder Bot - Cooldown', 'Gold Bot - Cooldown', 'Amp Bot - Cooldown', 'Flame Bot - Burn Stack', 'Thunder Bot - Linger Time', 'Gold Bot - Duration', 'Amp Bot - Duration', 'Common Enemy Health', 'Common Enemy Attack', 'Fast Enemy Health', 'Fast Enemy Attack', 'Fast Enemy Speed', 'Tank Enemy Health', 'Tank Enemy Attack', 'Ranged Enemy Health', 'Ranged Enemy Attack', 'Boss Health', 'Boss Attack', 'Protector Health', 'Protector Radius', 'Protector Damage Reduction', 'Ray Enemy Attack', 'Ray Enemy Health', 'Vampire Enemy Attack', 'Vampire Enemy Health', 'Scatter Enemy Attack', 'Scatter Enemy Health', 'Ranged Enemy Range', 'Common Drop Chance', 'Reroll Shards', 'Daily Mission shards', 'Module Shards Cost', 'Module Coin Cost', 'Rare Drop Chance', 'Unmerge Module', 'Shatter Shards', 'Cannon Effect Bans', 'Armor Effect Bans', 'Generator Effect Bans', 'Core Effect Bans', 'Assist Module Substats - Cannon', 'Assist Module Substats - Armor', 'Assist Module Substats - Generator', 'Assist Module Substats - Core', 'Assist Module Bonus - Cannon', 'Assist Module Bonus - Armor', 'Assist Module Bonus - Generator', 'Assist Module Bonus - Core', 'Battle Condition Reduction', 'Knockback Resistance', 'Thorns Resistance', 'Orb Resistance', 'Plasma Cannon Resistance', 'Death Ray Resistance', 'Armored Enemies', 'Enemy Speed', 'More Enemies', 'Enemy Attack Speed', "Fast's Ultimate", 'Ranged Ultimate', "Boss's Ultimate", "Basic's Ultimate", "Tank's Ultimate", "Protector's Ultimate", 'Ultimate Weapon Durations', 'Death Defy Down', 'Energy Shields Down', 'Enemy Level Skip Reduction']
- Formula cells: 0 (scanned 20000 cells - truncated)
- Preview (first 5 rows × 10 cols):
  - [None, 'Game Speed', None, 'Starting Cash', None, 'Workshop Attack Discount', None, 'Workshop Defense Discount', None, 'Workshop Utility Discount']
  - ['Lvl', 'Duration', 'Cost', 'Duration', 'Cost', 'Duration', 'Cost', 'Duration', 'Cost', 'Duration']
  - [1.0, datetime.timedelta(seconds=599), 300.0, datetime.timedelta(seconds=14), 30.0, datetime.timedelta(seconds=14), 30.0, datetime.timedelta(seconds=14), 30.0, datetime.timedelta(seconds=14)]
  - [2.0, datetime.timedelta(seconds=8940), 2500.0, datetime.timedelta(seconds=384), 71.0, datetime.timedelta(seconds=384), 71.0, datetime.timedelta(seconds=384), 71.0, datetime.timedelta(seconds=384)]
  - [3.0, datetime.timedelta(seconds=35940), 12000.0, datetime.timedelta(seconds=984), 178.0, datetime.timedelta(seconds=984), 178.0, datetime.timedelta(seconds=984), 178.0, datetime.timedelta(seconds=984)]

### Sheet: DVT_Laboratory2
- Dimensions: None rows × None cols
- First non-empty header-like row: 1
- Header values (non-empty): ['Lab Name', 'Tier', 'Wave']
- Formula cells: 0 (scanned 605 cells)
- Preview (first 5 rows × 10 cols):
  - ['Lab Name', 'Tier', 'Wave', None, None, None, None, None, None, None]
  - ['Game Speed', None, None, None, None, None, None, None, None, None]
  - ['Starting Cash', None, None, None, None, None, None, None, None, None]
  - ['Workshop Attack Discount', '2', 40.0, None, None, None, None, None, None, None]
  - ['Workshop Defense Discount', '2', 50.0, None, None, None, None, None, None, None]

### Sheet: Tier List
- Dimensions: None rows × None cols
- First non-empty header-like row: 1
- Header values (non-empty): ['Updated for version 27.0.3', 'Labs Sorted by Section', 'Conditional Section', 'Labs Sorted by Rank', 'Options', 'Labs Complete At', 'Target', 'Show locked Labs', True, 'Progress Bar', 'Time', '4x Boost']
- Formula cells: 6880 (scanned 20000 cells - truncated)
- Top formulas (up to 10):
  - =IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),"") (count=2465)
  - =IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),"Attack does not have any special interaction like health does with CL+. The lower health the enemy has compared to wave health, the higher value CL+ or BH+ is. Attack is a simple reducement in stats, leading it to be really low value even for eHp. This ch"&"anges little for tanks and bosses, however they are already the enemies you will want to and struggle with most to kill") (count=22)
  - =IFERROR(VLOOKUP("Tier 1",'_IDS'!$BZ$3:$DT$23, 2, FALSE) > 30, TRUE) (count=15)
  - =IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),"Resistances get far weaker than most battle conditions with how they substract the effect") (count=10)
  - =IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),"Basically another reroll shards lab but arguably worse") (count=8)
  - =IFERROR(VLOOKUP("Tier 19",'_IDS'!$BZ$3:$DT$23, 2, FALSE) > 50, true) (count=8)
  - =IFERROR(VLOOKUP("Tier 10",'_IDS'!$BZ$3:$DT$23, 2, FALSE) > 40, true) (count=7)
  - =IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),"Great complementary source of crowd control") (count=6)
  - =IFERROR(VLOOKUP("Tier 19",'_IDS'!$BZ$3:$DT$23, 2, FALSE) > 60, true) (count=6)
  - =IFERROR(VLOOKUP("Tier 19",'_IDS'!$BZ$3:$DT$23, 2, FALSE) > 500, true) (count=6)
- Preview (first 5 rows × 10 cols):
  - [None, 'Updated for version 27.0.3', None, 'Labs Sorted by Section', None, None, 'Conditional Section', None, None, None]
  - [None, 'Tier', 'Lab Name', 'Ranking', None, 'Notes', 'IsUnlocked', 'Ranking', None, 'Notes']
  - [None, 'T1', 'Game Speed', 'S+', None, 'Makes everything better. First lab to take to max', '=IFERROR(VLOOKUP("Tier 1",\'_IDS\'!$BZ$3:$DT$23, 2, FALSE) > 30, TRUE)', <openpyxl.worksheet.formula.ArrayFormula object at 0x7ff583183040>, None, '=if(ISBLANK(F3),J2, F3)']
  - [None, None, 'Starting Cash', 'F', None, 'Irrelevant, easily outdone by enemy kills and even cash/wave', '=IFERROR(VLOOKUP("Tier 1",\'_IDS\'!$BZ$3:$DT$23, 2, FALSE) > 30, TRUE)', <openpyxl.worksheet.formula.ArrayFormula object at 0x7ff583181120>, None, '=if(ISBLANK(F4),J3, F4)']
  - [None, 'T2', 'Workshop Attack Discount', 'D', None, 'Gaining more coins is more beneficial then spending less coins, utility can be useful for ELS later on. Retroactive on respecs', '=IFERROR(VLOOKUP("Tier 2",\'_IDS\'!$BZ$3:$DT$23, 2, FALSE) > 40, true)', <openpyxl.worksheet.formula.ArrayFormula object at 0x7ff5831838b0>, None, '=if(ISBLANK(F5),J4, F5)']

### Sheet: Lab Boost Calculator
- Dimensions: None rows × None cols
- First non-empty header-like row: 7
- Header values (non-empty): ['Hrs farming / day', 'Hrs in Tournaments', 'Cells / hr', 'Cells / hr final', 'Max 5x boost', 'How long is a run?']
- Formula cells: 34 (scanned 294 cells)
- Top formulas (up to 10):
  - =G8*(C8/24)*((24-D8*2/7)/24) (count=1)
  - <openpyxl.worksheet.formula.ArrayFormula object at 0x7ff5831f1060> (count=1)
  - =150% (count=1)
  - =IFERROR(XLOOKUP($K12,$C$12:$C$17,$B$12:$B$17),"1") (count=1)
  - <openpyxl.worksheet.formula.ArrayFormula object at 0x7ff5831f1bd0> (count=1)
  - =B13/B12 (count=1)
  - =C13/C12 (count=1)
  - =D13/E13 (count=1)
  - =IFERROR(XLOOKUP($K13,$C$12:$C$17,$B$12:$B$17),"1") (count=1)
  - =LET(
  MaxFullBoostCost, XLOOKUP($K$8,$B$12:$B$17,$C$12:$C$17,0),
  NextBoostCost, XLOOKUP($K$8+IF($K$8 < 2,0.5, 1),$B$12:$B$17,$C$12:$C$17, "", -1),
  RemainingLabSlot, COUNTA($I14:$I$16),

  IFERROR(
  IF(MaxFullBoostCost*RemainingLabSlot+NextBoostCost+SUM($K$12:$K12)<=$I$8,
    NextBoostCost,
    MaxFullBoostCost),0
)) (count=1)
- Preview (first 5 rows × 10 cols):
  - [None, None, None, None, None, None, None, None, None, None]
  - [None, 'Which boost can you afford?\nType in Cells / hr as well as the Hrs per day you are spending on farming and the Hrs in Tournaments for \neach tournament day below and see what boosts you can sustain constantly.\nAlso see, how many you would need to jump to the next threshold', None, None, None, None, None, None, None, None]
  - [None, None, None, None, None, None, None, None, None, None]
  - [None, None, None, None, None, None, None, None, None, None]
  - [None, None, None, None, None, None, None, None, None, None]

### Sheet: Short Lab Path
- Dimensions: None rows × None cols
- First non-empty header-like row: 3
- Header values (non-empty): [1.0, 'LAB TIME PATH', 'Explainations']
- Formula cells: 1588 (scanned 16920 cells)
- Top formulas (up to 10):
  - =IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),"") (count=689)
  - =IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),"Coins / Wave") (count=20)
  - =IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),"Starting Cash") (count=20)
  - =IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),"Cash / Wave") (count=18)
  - =IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),25.0) (count=6)
  - =IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),13.0) (count=4)
  - =IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),"Cash Bonus") (count=3)
  - =IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),9.0) (count=3)
  - =IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),10.0) (count=3)
  - =IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),11.0) (count=3)
- Preview (first 5 rows × 10 cols):
  - [None, None, None, None, None, None, None, None, None, None]
  - [None, None, None, None, None, '=IFERROR(__xludf.DUMMYFUNCTION("IF(F6<>"""", SPARKLINE(H6:H705), ""Completed ! 🎉"")"),"")', None, None, None, None]
  - [None, None, 1.0, None, 'LAB TIME PATH', None, None, None, None, None]
  - [None, None, 2.0, None, None, '="Upgrade (" & COUNTA(F6:F705) & IF(F200<>"", "+", ) & ")"', 'Level', 'Duration', 'Cost', None]
  - [None, None, 3.0, None, None, None, None, None, None, None]

### Sheet: Interactive Thorns
- Dimensions: None rows × None cols
- First non-empty header-like row: 6
- Header values (non-empty): ['WS Thorns', 'Relics', 'Sub Thorns', 'Plasma Cannon', 'Vault Thorns', 'BC Thorns', 'SF']
- Formula cells: 310 (scanned 744 cells)
- Top formulas (up to 10):
  - =$B$10 (count=2)
  - =MAX('Master Sheet'!BF2:BG2)*1% (count=1)
  - ='Master Sheet'!BK6 (count=1)
  - =IDS_MOD_ARMOR_SUBSTAT(J5, "Thorns Damage") (count=1)
  - =0.26+0.04*'Master Sheet'!BK2 (count=1)
  - =IF('Master Sheet'!BL2, (1+'Master Sheet'!AB25)*5%, "🔒") (count=1)
  - ='Master Sheet'!BK9 (count=1)
  - =1% * 'Master Sheet'!M14 (count=1)
  - =LET(
  Relic, 1+H7,
  Vault, 1+ N7,
  BC, P7,
  Thorn, (F7 + J7) * Vault * Relic,
  RoundedThorn, ROUND(Thorn, 2),
RoundedThorn * BC)  (count=1)
  - =IF($B$10>0, ROUNDUP(100/(C$9*$B10*100),0), ) (count=1)
- Preview (first 5 rows × 10 cols):
  - [None, None, None, None, None, None, None, None, None, None]
  - [None, None, '@phoenix345 -- Wall Thorns v1.4 -- Number of wall hits to kill elites, bosses, bosses with plasma cannon, and elites with plasma cannon mastery,\nfor Wall Thorns (1-20%), with thorns Relics, Sub-mod (0-10%) and Vault thorns (5%)', None, None, None, None, None, None, None]
  - [None, None, None, None, None, None, None, None, None, None]
  - [None, None, None, None, None, None, None, None, None, None]
  - [None, None, None, None, None, None, None, None, None, 'Farming']

### Sheet: ELS BC Reduction
- Dimensions: None rows × None cols
- First non-empty header-like row: 3
- Header values (non-empty): ['Heat Wave', 'ELS BC Level', 'ELS BC Value', 'Original level', 'Original Value']
- Formula cells: 40 (scanned 110 cells)
- Top formulas (up to 10):
  - ='Master Sheet'!BA2 (count=1)
  - =$D$1*2% (count=1)
  - =MAX(D4-$D$1,1) (count=1)
  - =($E$4/$D$4)*B4*(1-$D$2) (count=1)
  - =MAX(D5-$D$1,1) (count=1)
  - =($E$4/$D$4)*B5*(1-$D$2) (count=1)
  - =MAX(D6-$D$1,1) (count=1)
  - =($E$4/$D$4)*B6*(1-$D$2) (count=1)
  - =MAX(D7-$D$1,1) (count=1)
  - =($E$4/$D$4)*B7*(1-$D$2) (count=1)
- Preview (first 5 rows × 10 cols):
  - ['Battle Condition Reduction', None, None, "='Master Sheet'!BA2", None, None, None, None, None, None]
  - ['Lab Reduction', None, None, '=$D$1*2%', None, None, None, None, None, None]
  - ['Heat Wave', 'ELS BC Level', 'ELS BC Value', 'Original level', 'Original Value', None, None, None, None, None]
  - [1.0, '=MAX(D4-$D$1,1)', '=($E$4/$D$4)*B4*(1-$D$2)', 3.0, -0.01, None, None, None, None, None]
  - [20.0, '=MAX(D5-$D$1,1)', '=($E$4/$D$4)*B5*(1-$D$2)', 6.0, -0.02, None, None, None, None, None]

### Sheet: Elites Spawncap
- Dimensions: None rows × None cols
- First non-empty header-like row: 3
- Header values (non-empty): ['Std. Perk Level 🔗', 'Speed Perk Wave 🔗', 'Game Speed', 'Final Speed', 'Cells WS+ 🔗', 'Initial Wave Duration', 'Final Wave Duration']
- Formula cells: 522 (scanned 1716 cells)
- Top formulas (up to 10):
  - ='Master Sheet'!AG5 (count=1)
  - =I4+1+E4/100 (count=1)
  - ='Master Sheet'!M16 (count=1)
  - =TIME(,,((35*9)+38)/10/I4) (count=1)
  - =TIME(,,SUM(((35*9)+38)/10/K4)) (count=1)
  - =D9/0.9 (count=1)
  - =E9/0.9 (count=1)
  - =F9/0.9 (count=1)
  - =G9/0.9 (count=1)
  - =H9/0.9 (count=1)
- Preview (first 5 rows × 10 cols):
  - [None, None, None, None, None, None, None, None, None, None]
  - [None, None, 'Player Data Used', None, None, None, None, None, None, None]
  - [None, None, None, None, 'Std. Perk Level 🔗', None, 'Speed Perk Wave 🔗', None, 'Game Speed', None]
  - [None, None, None, None, "='Master Sheet'!AG5", None, 500.0, None, 5.0, None]
  - [None, None, None, None, None, None, None, None, None, None]

### Sheet: EXPORT
- Dimensions: None rows × None cols
- First non-empty header-like row: 2
- Header values (non-empty): ['Total', '=SUM(C5:C216)', '=C2/E2', '=SUM(E5:E216)']
- Formula cells: 635 (scanned 1296 cells)
- Top formulas (up to 10):
  - =SUM(C5:C216) (count=1)
  - =C2/E2 (count=1)
  - =SUM(E5:E216) (count=1)
  - ='Master Sheet'!C2 (count=1)
  - ='Master Sheet'!D2 (count=1)
  - ='Master Sheet'!E2 (count=1)
  - ='Master Sheet'!C3 (count=1)
  - ='Master Sheet'!D3 (count=1)
  - ='Master Sheet'!E3 (count=1)
  - ='Master Sheet'!C4 (count=1)
- Preview (first 5 rows × 10 cols):
  - ['Lv2', None, None, None, None, None, None, None, None, None]
  - [None, 'Total', '=SUM(C5:C216)', '=C2/E2', '=SUM(E5:E216)', None, None, None, None, None]
  - [None, None, None, None, None, None, None, None, None, None]
  - [None, 'Labs', 'Level', 'Target', 'Max', None, None, None, None, None]
  - [None, 'Game Speed', "='Master Sheet'!C2", "='Master Sheet'!D2", "='Master Sheet'!E2", None, None, None, None, None]
- EXPORT columns (5): ['Lv2', 'Unnamed: 1', 'Unnamed: 2', 'Unnamed: 3', 'Unnamed: 4']
- EXPORT row count: 215

## Copy of Modules v5.12.xlsx
- Size: 3358721 bytes
- Sheets: Home Page, IDS, Master Sheet, Inventory, _IDS, Presets, DVT_Modules, Mods Obtained, Mods Obtained (old), Planner, Tracker, Reroll Calculator v3, EXPORT, Optimal Assist levels, Shard Path, Overview, Substats, Module Costs, DVT_Laboratory

### Sheet: Home Page
- Dimensions: None rows × None cols
- First non-empty header-like row: 4
- Header values (non-empty): ['=HYPERLINK("https://docs.google.com/spreadsheets/d/1KCxnSAvhstAbFdBSYSO_3bKUPtCFX42Eb7Z13agPU9s/copy", "Modules Initial Link")', 'Sheet Tab', 'Creator', 'Main Contributor', 'Helpers']
- Formula cells: 8 (scanned 612 cells)
- Top formulas (up to 10):
  - =HYPERLINK("https://docs.google.com/spreadsheets/d/1KCxnSAvhstAbFdBSYSO_3bKUPtCFX42Eb7Z13agPU9s/copy", "Modules Initial Link") (count=1)
  - =IFERROR(__xludf.DUMMYFUNCTION("IMPORTRANGE(""1KCxnSAvhstAbFdBSYSO_3bKUPtCFX42Eb7Z13agPU9s"", ""'Home Page'!B12:C13"")"),"v5.12") (count=1)
  - =IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),"feat: Optimal Assist Levels ""Apply"" button") (count=1)
  - =IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),"v5.11.1") (count=1)
  - =IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),"fix: Optimal Assist Levels fix for Assist Level = 0") (count=1)
  - =HYPERLINK(IF('_IDS'!AB1="✅",'_IDS'!AF1, "https://docs.google.com/spreadsheets/d/1wVLlvWfmcjHRkAnQJzAQu_YZo_eW1FXMVTfYYQnF7Xc")&"#gid=2001828042", "RPC Mastery") (count=1)
  - =IFERROR(__xludf.DUMMYFUNCTION("IMPORTRANGE(""1eCPPuQOE3Pyh8HhnApEMK3RFIutkUjWd61ppVImwWk8"", ""_Giveaway_summary!A1:A2"")"),"⚠️ 2 Giveaway(s) running - 2 Feb | 5 Feb") (count=1)
  - =IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),"Giveaway Details") (count=1)
- Preview (first 5 rows × 10 cols):
  - [None, None, None, None, None, None, None, None, None, None]
  - [None, 'Modules', None, None, None, None, None, None, None, None]
  - [None, None, None, None, None, None, None, None, None, None]
  - [None, '=HYPERLINK("https://docs.google.com/spreadsheets/d/1KCxnSAvhstAbFdBSYSO_3bKUPtCFX42Eb7Z13agPU9s/copy", "Modules Initial Link")', None, None, None, None, 'Sheet Tab', 'Creator', 'Main Contributor', 'Helpers']
  - [None, None, None, None, None, None, None, None, None, None]

### Sheet: IDS
- Dimensions: None rows × None cols
- First non-empty header-like row: 6
- Header values (non-empty): ["IDS Master's ID       ➡️", '18XbHJtHzu8tjqnP_9JcsZFA6jIwjOKRYmzBzOYBMv2I', '=IFERROR(__xludf.DUMMYFUNCTION("IFERROR(C6.url, IFS(LEFT(C6,8)=""https://"", C6, LEN(C6)=44, ""https://docs.google.com/spreadsheets/d/"" & C6 & ""/edit"", TRUE, C6))"),"https://docs.google.com/spreadsheets/d/18XbHJtHzu8tjqnP_9JcsZFA6jIwjOKRYmzBzOYBMv2I/edit")', '=IFERROR(__xludf.DUMMYFUNCTION("IF(D6<>"""", IF(IMPORTRANGE(D6,""EXPORT!A1"") = F6, ""✅"", ""Wrong ID or Version""), """")"),"✅")', 'v2']
- Formula cells: 4 (scanned 218 cells)
- Top formulas (up to 10):
  - =IFERROR(__xludf.DUMMYFUNCTION("IFERROR(C6.url, IFS(LEFT(C6,8)=""https://"", C6, LEN(C6)=44, ""https://docs.google.com/spreadsheets/d/"" & C6 & ""/edit"", TRUE, C6))"),"https://docs.google.com/spreadsheets/d/18XbHJtHzu8tjqnP_9JcsZFA6jIwjOKRYmzBzOYBMv2I/edit") (count=1)
  - =IFERROR(__xludf.DUMMYFUNCTION("IF(D6<>"""", IF(IMPORTRANGE(D6,""EXPORT!A1"") = F6, ""✅"", ""Wrong ID or Version""), """")"),"✅") (count=1)
  - =HYPERLINK("https://docs.google.com/spreadsheets/d/1osjoqKmMwtOWs7Up3e21-3ofN1RHOjsgKV6y3dc6rgE/copy", "1️⃣ Copy Me") (count=1)
  - =IFS(
  ISERROR(E6), "3️⃣ Click on #REF! and then AUTHORISE ↗",
  E6="", "2️⃣ Please input your IDS Master's ID here ⤴️",
  E6="✅", HYPERLINK(D6, "Go to my IDS Master Sheet"),
  TRUE, "") (count=1)
- Preview (first 5 rows × 10 cols):
  - [None, None, None, None, None, None, None, None, None, None]
  - [None, 'The IDS System', None, None, None, None, None, None, 'Looking for the Import script ? Just run it as you were doing it before, but from IDS Master.\nIt will let you import every new versions at once!', None]
  - [None, None, None, None, None, None, None, None, None, None]
  - [None, 'This Sheet ID is :', '1mz0hSpsng0Kzlz8xk0VEyRgaE62Gzj5kNLu3Vp-4gGE', None, None, None, None, None, None, None]
  - [None, None, None, None, None, None, None, None, None, None]

### Sheet: Master Sheet
- Dimensions: None rows × None cols
- First non-empty header-like row: 1
- Header values (non-empty): ['=IF(\'_IDS\'!C1="✅", HYPERLINK(\'_IDS\'!B1, "Go to my Laboratory Sheet"), "Labs")', 'Level', 'Max', '=IF(\'_IDS\'!AO1="✅", HYPERLINK(\'_IDS\'!AN1, "Go to my Relic Sheet"), "Relic")', 'Bonus']
- Formula cells: 24 (scanned 189 cells)
- Top formulas (up to 10):
  - =IF('_IDS'!C1="✅", HYPERLINK('_IDS'!B1, "Go to my Laboratory Sheet"), "Labs") (count=1)
  - =IF('_IDS'!AO1="✅", HYPERLINK('_IDS'!AN1, "Go to my Relic Sheet"), "Relic") (count=1)
  - =IDS_LAB_LEVEL(B2) (count=1)
  - =IDS_RELIC_STAT(F2) (count=1)
  - =IDS_LAB_LEVEL(B3) (count=1)
  - =IDS_LAB_LEVEL(B4) (count=1)
  - =COUNTA(OFFSET(DVT_Laboratory!$B$3, 0, MATCH(A2,DVT_Laboratory!$B$1:I$1, 0)-1, 100, 1)) (count=1)
  - =IF('_IDS'!AF1="✅", HYPERLINK('_IDS'!AE1, "Go to my Vault Sheet"), "Vault Upgrade") (count=1)
  - =IDS_LAB_LEVEL(B5) (count=1)
  - =IDS_VAULT_STAT(F5) (count=1)
- Preview (first 5 rows × 10 cols):
  - [None, '=IF(\'_IDS\'!C1="✅", HYPERLINK(\'_IDS\'!B1, "Go to my Laboratory Sheet"), "Labs")', 'Level', 'Max', None, '=IF(\'_IDS\'!AO1="✅", HYPERLINK(\'_IDS\'!AN1, "Go to my Relic Sheet"), "Relic")', 'Bonus', None, None, None]
  - ['LABS', 'Labs Coin Discount', '=IDS_LAB_LEVEL(B2)', 99.0, 'VAULT TREE', 'Lab Speed', '=IDS_RELIC_STAT(F2)', None, None, None]
  - [None, 'Labs Speed', '=IDS_LAB_LEVEL(B3)', 99.0, None, None, None, None, None, None]
  - [None, 'Package After Boss', '=IDS_LAB_LEVEL(B4)', '=COUNTA(OFFSET(DVT_Laboratory!$B$3, 0, MATCH(A2,DVT_Laboratory!$B$1:I$1, 0)-1, 100, 1))', None, '=IF(\'_IDS\'!AF1="✅", HYPERLINK(\'_IDS\'!AE1, "Go to my Vault Sheet"), "Vault Upgrade")', 'Bonus', None, None, None]
  - [None, 'Recovery Package Chance', '=IDS_LAB_LEVEL(B5)', 20.0, None, 'Discount Rerolls', '=IDS_VAULT_STAT(F5)', None, None, None]

### Sheet: Inventory
- Dimensions: None rows × None cols
- First non-empty header-like row: 3
- Header values (non-empty): ['🔵 CANNON', 'Astral Deliverance', 'Being Annihilator', 'Death Penalty', 'Havoc Bringer', 'Shrink Ray', 'Amplifying Strike', 'Any Other', 'Any Other 2']
- Formula cells: 576 (scanned 2430 cells)
- Top formulas (up to 10):
  - =CAP_MOD_LEVEL($D5,F5) (count=1)
  - =IF(F5="None",1,MODSTAT_CANNON(F5,G5)) (count=1)
  - =CAP_MOD_LEVEL($D5,K5) (count=1)
  - =IF(K5="None",1,MODSTAT_CANNON(K5,L5)) (count=1)
  - =CAP_MOD_LEVEL($D5,P5) (count=1)
  - =IF(P5="None",1,MODSTAT_CANNON(P5,Q5)) (count=1)
  - =CAP_MOD_LEVEL($D5,U5) (count=1)
  - =IF(U5="None",1,MODSTAT_CANNON(U5,V5)) (count=1)
  - =CAP_MOD_LEVEL($D5,Z5) (count=1)
  - =IF(Z5="None",1,MODSTAT_CANNON(Z5,AA5)) (count=1)
- Preview (first 5 rows × 10 cols):
  - [None, None, None, None, None, 'Module Inventory', None, None, None, None]
  - [None, None, None, None, None, None, None, None, None, None]
  - ['🔵 CANNON', None, None, None, None, 'Astral Deliverance', None, None, None, None]
  - [None, None, None, 'Highest Level', None, 'Rarity', 'Level', 'Stat', None, None]
  - [None, 'Tower Damage', None, 155.0, None, 'Mythic+', '=CAP_MOD_LEVEL($D5,F5)', '=IF(F5="None",1,MODSTAT_CANNON(F5,G5))', None, None]

### Sheet: _IDS
- Dimensions: None rows × None cols
- First non-empty header-like row: 1
- Header values (non-empty): ['=IFERROR(__xludf.DUMMYFUNCTION("IMPORTRANGE(IF(IDS!E6=""✅"", IDS!D6, ""1osjoqKmMwtOWs7Up3e21-3ofN1RHOjsgKV6y3dc6rgE""), ""_IDS!A1:BY212"")"),"Labs")', '=IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),"https://docs.google.com/spreadsheets/d/1yLi6Ni4nZr0Wfct7MmbyNRRi5v6fR62t0kdI-g8NeNo/edit")', '=IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),"✅")', '=IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),"v2.3.2")', '=IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),"WS")', '=IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),"https://docs.google.com/spreadsheets/d/1462mmIeTEmChEYwwpDWacv611QCRW9n-Dvz8oyOQ798/edit")', '=IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),"✅")', '=IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),"v2.2.8")', '=IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),"WS+")', '=IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),"UWs")', '=IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),"https://docs.google.com/spreadsheets/d/1aLEWX2qblJJt96I6QduS_Fp2DjMO6rNToPrUBWGI5BU/edit")', '=IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),"✅")', '=IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),"v2.1.2")', '=IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),"Cards")', '=IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),"https://docs.google.com/spreadsheets/d/1HMQwNLTvcw7aXmjjL7cXmZSdjAF_62ehWpwDIdjqEGs/edit")', '=IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),"✅")', '=IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),"Cards Presets")', '=IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),"v2.2.3")', '=IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),"Relics")', '=IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),"https://docs.google.com/spreadsheets/d/1jtZ_RhMszIY0NzPm-kNhYg_w5D8WDm9tXSJatvVpWDU/edit")', '=IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),"✅")', '=IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),"Vault")', '=IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),"")', '=IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),"Bots")', '=IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),"https://docs.google.com/spreadsheets/d/1gopHNYu4SgI0UbRvscCV4_C1gct7FXr5GBBcjCzCxC0/edit")', '=IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),"✅")', '=IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),"v2.2")', '=IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),"Themes & Songs")', '=IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),"https://docs.google.com/spreadsheets/d/1umYUbdc7TGYJhqFv662Yol9PGzfECdpLYxl4ElV6UwQ/edit")', '=IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),"✅")', '=IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),"Modules")', '=IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),"https://docs.google.com/spreadsheets/d/1mz0hSpsng0Kzlz8xk0VEyRgaE62Gzj5kNLu3Vp-4gGE/edit")', '=IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),"✅")', '=IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),"v5.12")', '=IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),"Guardians")', '=IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),"https://docs.google.com/spreadsheets/d/19vecjglXSr9t51C6vJy-lMGk1xH4h52ytBr-uyKxLcM/edit")', '=IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),"✅")', '=IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),"v2.2.5")']
- Formula cells: 2481 (scanned 20000 cells - truncated)
- Top formulas (up to 10):
  - =IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),"") (count=186)
  - =IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),0.0) (count=171)
  - =IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),99.0) (count=59)
  - =IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),FALSE) (count=54)
  - =IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),20.0) (count=50)
  - =IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),30.0) (count=49)
  - =IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),7.0) (count=46)
  - =IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),1.0) (count=45)
  - =IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),TRUE) (count=36)
  - =IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),9.0) (count=33)
- Preview (first 5 rows × 10 cols):
  - ['=IFERROR(__xludf.DUMMYFUNCTION("IMPORTRANGE(IF(IDS!E6=""✅"", IDS!D6, ""1osjoqKmMwtOWs7Up3e21-3ofN1RHOjsgKV6y3dc6rgE""), ""_IDS!A1:BY212"")"),"Labs")', '=IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),"https://docs.google.com/spreadsheets/d/1yLi6Ni4nZr0Wfct7MmbyNRRi5v6fR62t0kdI-g8NeNo/edit")', '=IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),"✅")', '=IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),"v2.3.2")', '=IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),"WS")', '=IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),"https://docs.google.com/spreadsheets/d/1462mmIeTEmChEYwwpDWacv611QCRW9n-Dvz8oyOQ798/edit")', '=IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),"✅")', '=IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),"v2.2.8")', None, None]
  - ['=IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),"Game Speed")', '=IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),7.0)', '=IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),7.0)', '=IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),7.0)', '=IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),"U")', '=IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),"Workshop Upgrade")', '=IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),"Farming")', None, '=IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),"Tourney")', None]
  - ['=IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),"Starting Cash")', '=IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),6.0)', None, '=IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),99.0)', None, None, '=IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),"¢ Level")', '=IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),"$ Level")', '=IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),"¢ Level")', '=IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),"$ Level")']
  - ['=IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),"Workshop Attack Discount")', '=IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),16.0)', None, '=IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),99.0)', None, '=IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),"Damage")', '=IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),5750.0)', '=IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),6000.0)', '=IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),5750.0)', '=IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),6000.0)']
  - ['=IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),"Workshop Defense Discount")', '=IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),19.0)', None, '=IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),99.0)', None, '=IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),"Attack Speed")', '=IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),99.0)', '=IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),99.0)', '=IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),99.0)', '=IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),99.0)']

### Sheet: Presets
- Dimensions: None rows × None cols
- First non-empty header-like row: 2
- Header values (non-empty): ['Assist Slots', 'Assist Slot', '=IF(F2, "Unlocked", "Locked")', False, 'Module Presets', 'Farming', 'Tourney', 'Testing']
- Formula cells: 12 (scanned 408 cells)
- Top formulas (up to 10):
  - =IF(F2, "Unlocked", "Locked") (count=1)
  - <openpyxl.worksheet.formula.ArrayFormula object at 0x7ff582f46230> (count=1)
  - <openpyxl.worksheet.formula.ArrayFormula object at 0x7ff582f46290> (count=1)
  - =IF(F8, "Unlocked", "Locked") (count=1)
  - <openpyxl.worksheet.formula.ArrayFormula object at 0x7ff582f462f0> (count=1)
  - <openpyxl.worksheet.formula.ArrayFormula object at 0x7ff582f46350> (count=1)
  - =IF(F14, "Unlocked", "Locked") (count=1)
  - <openpyxl.worksheet.formula.ArrayFormula object at 0x7ff582f463b0> (count=1)
  - <openpyxl.worksheet.formula.ArrayFormula object at 0x7ff582f46410> (count=1)
  - =IF(F20, "Unlocked", "Locked") (count=1)
- Preview (first 5 rows × 10 cols):
  - ['🔵 CANNON', None, None, None, None, None, None, None, None, None]
  - [None, None, 'Assist Slots', 'Assist Slot', '=IF(F2, "Unlocked", "Locked")', False, None, 'Module Presets', 'Farming', None]
  - [None, None, None, 'Rarity Cap', 'Epic', None, None, None, None, None]
  - [None, None, None, 'Multiplier Cap', <openpyxl.worksheet.formula.ArrayFormula object at 0x7ff582f46800>, '00 | 1% | Cost 0 ⧌ | Next 15 ⧌', None, None, 'Primary Slot', 'Amplifying Strike']
  - [None, None, None, 'Substat Cap', <openpyxl.worksheet.formula.ArrayFormula object at 0x7ff582f46860>, '00 | 1% | Cost 0 ⧌ | Next 15 ⧌', None, None, 'Assist Slot', None]

### Sheet: DVT_Modules
- Dimensions: None rows × None cols
- First non-empty header-like row: 1
- Header values (non-empty): ['RARITY', 'Cannon', 'Armor', 'Generator', 'Core', 'Assist level', 'Cost', '%', 'Dropdown', 'Substat Names', 'Substat Values', 'Format', 'RAW', 'Formated', 'RAW', 'Formated', 'RAW', 'Formated', 'RAW', 'Formated', 'RAW', 'Formated', 'RAW', 'Formated']
- Formula cells: 886 (scanned 5767 cells)
- Top formulas (up to 10):
  - ="+0%" (count=26)
  - =+2% (count=10)
  - =+6% (count=8)
  - =+4% (count=8)
  - =+8% (count=7)
  - ="+0" (count=6)
  - =+1 (count=4)
  - =+12% (count=4)
  - =+10% (count=4)
  - =+40% (count=3)
- Preview (first 5 rows × 10 cols):
  - [None, 'RARITY', 'Cannon', 'Armor', 'Generator', 'Core', None, 'Assist level', 'Cost', '%']
  - ['Modules', 'Base stat', 'Damage', 'Hp', 'Coin', 'UW', None, 0.0, '=H2*3', '=(H2+1)*1%']
  - [None, 'Common', 0.012, 0.012, 0.011, 0.04, None, '=H2+1', '=H3*3+12', '=(H3+1)*1%']
  - [None, 'Rare', 0.032, 0.032, 0.013, 0.06, None, '=H3+1', '=H4*3+12', '=(H4+1)*1%']
  - [None, 'Rare+', 0.052, 0.052, 0.016, 0.09, None, '=H4+1', '=H5*3+12', '=(H5+1)*1%']

### Sheet: Mods Obtained
- Dimensions: None rows × None cols
- First non-empty header-like row: 3
- Header values (non-empty): ['Mod', '# Pulled', '%Ca', '%T', 'Mod', '# Pulled', '%G', '%T']
- Formula cells: 58 (scanned 891 cells)
- Top formulas (up to 10):
  - =iferror(C4/C$9, 0) (count=1)
  - =iferror(C4/B$21, 0) (count=1)
  - =iferror(H4/H$9, 0) (count=1)
  - =iferror(H4/B$21, 0) (count=1)
  - =iferror(C5/C$9, 0) (count=1)
  - =iferror(C5/B$21, 0) (count=1)
  - =iferror(H5/H$9, 0) (count=1)
  - =iferror(H5/B$21, 0) (count=1)
  - =iferror(C6/C$9, 0) (count=1)
  - =iferror(C6/B$21, 0) (count=1)
- Preview (first 5 rows × 10 cols):
  - [None, None, None, None, None, None, None, None, None, None]
  - [None, 'Cannons', None, None, None, None, 'Generators', None, None, None]
  - [None, 'Mod', '# Pulled', '%Ca', '%T', None, 'Mod', '# Pulled', '%G', '%T']
  - [None, 'AD', 0.0, '=iferror(C4/C$9, 0)', '=iferror(C4/B$21, 0)', None, 'BHD', 0.0, '=iferror(H4/H$9, 0)', '=iferror(H4/B$21, 0)']
  - [None, 'BA', 0.0, '=iferror(C5/C$9, 0)', '=iferror(C5/B$21, 0)', None, 'GC', 0.0, '=iferror(H5/H$9, 0)', '=iferror(H5/B$21, 0)']

### Sheet: Mods Obtained (old)
- Dimensions: None rows × None cols
- First non-empty header-like row: 3
- Header values (non-empty): ['Mod', '# Pulled', '%Ca', '%T', 'Mod', '# Pulled', '%G', '%T']
- Formula cells: 55 (scanned 729 cells)
- Top formulas (up to 10):
  - =iferror(C4/C$9, 0) (count=1)
  - =iferror(C4/B$21, 0) (count=1)
  - =iferror(H4/H$9, 0) (count=1)
  - =iferror(H4/B$21, 0) (count=1)
  - =iferror(C5/C$9, 0) (count=1)
  - =iferror(C5/B$21, 0) (count=1)
  - =iferror(H5/H$9, 0) (count=1)
  - =iferror(H5/B$21, 0) (count=1)
  - =iferror(C6/C$9, 0) (count=1)
  - =iferror(C6/B$21, 0) (count=1)
- Preview (first 5 rows × 10 cols):
  - [None, None, None, None, None, None, None, None, None, None]
  - [None, 'Cannons', None, None, None, None, 'Generators', None, None, None]
  - [None, 'Mod', '# Pulled', '%Ca', '%T', None, 'Mod', '# Pulled', '%G', '%T']
  - [None, 'AD', 0.0, '=iferror(C4/C$9, 0)', '=iferror(C4/B$21, 0)', None, 'BHD', 0.0, '=iferror(H4/H$9, 0)', '=iferror(H4/B$21, 0)']
  - [None, 'BA', 0.0, '=iferror(C5/C$9, 0)', '=iferror(C5/B$21, 0)', None, 'GC', 0.0, '=iferror(H5/H$9, 0)', '=iferror(H5/B$21, 0)']

### Sheet: Planner
- Dimensions: None rows × None cols
- First non-empty header-like row: 3
- Header values (non-empty): ['🔵 CANNON', <openpyxl.worksheet.formula.ArrayFormula object at 0x7ff582f46890>, <openpyxl.worksheet.formula.ArrayFormula object at 0x7ff582f46140>, 'Astral Deliverance', <openpyxl.worksheet.formula.ArrayFormula object at 0x7ff582f44400>, 'Being Annihilator', <openpyxl.worksheet.formula.ArrayFormula object at 0x7ff582f47010>, 'Death Penalty', <openpyxl.worksheet.formula.ArrayFormula object at 0x7ff582f46410>, 'Havoc Bringer', <openpyxl.worksheet.formula.ArrayFormula object at 0x7ff582f46f50>, 'Shrink Ray', <openpyxl.worksheet.formula.ArrayFormula object at 0x7ff582f463b0>, 'Amplifying Strike', <openpyxl.worksheet.formula.ArrayFormula object at 0x7ff582f47100>, 'Any Other', <openpyxl.worksheet.formula.ArrayFormula object at 0x7ff582f46500>, 'Any Other 2']
- Formula cells: 1974 (scanned 4212 cells)
- Top formulas (up to 10):
  - <openpyxl.worksheet.formula.ArrayFormula object at 0x7ff582f463e0> (count=1)
  - <openpyxl.worksheet.formula.ArrayFormula object at 0x7ff582f45d80> (count=1)
  - <openpyxl.worksheet.formula.ArrayFormula object at 0x7ff582f46a10> (count=1)
  - <openpyxl.worksheet.formula.ArrayFormula object at 0x7ff582f45ba0> (count=1)
  - <openpyxl.worksheet.formula.ArrayFormula object at 0x7ff5831a08e0> (count=1)
  - <openpyxl.worksheet.formula.ArrayFormula object at 0x7ff5831a0dc0> (count=1)
  - <openpyxl.worksheet.formula.ArrayFormula object at 0x7ff5831a0670> (count=1)
  - <openpyxl.worksheet.formula.ArrayFormula object at 0x7ff5831a00d0> (count=1)
  - <openpyxl.worksheet.formula.ArrayFormula object at 0x7ff5831834f0> (count=1)
  - <openpyxl.worksheet.formula.ArrayFormula object at 0x7ff583183a00> (count=1)
- Preview (first 5 rows × 10 cols):
  - [None, None, <openpyxl.worksheet.formula.ArrayFormula object at 0x7ff583058eb0>, None, None, None, 'Module Planner', None, None, None]
  - [None, None, <openpyxl.worksheet.formula.ArrayFormula object at 0x7ff583058f10>, None, None, None, None, None, None, None]
  - ['🔵 CANNON', None, <openpyxl.worksheet.formula.ArrayFormula object at 0x7ff583058f70>, None, None, <openpyxl.worksheet.formula.ArrayFormula object at 0x7ff583058fd0>, 'Astral Deliverance', None, None, None]
  - [None, None, <openpyxl.worksheet.formula.ArrayFormula object at 0x7ff5830592d0>, 'Highest Level', None, <openpyxl.worksheet.formula.ArrayFormula object at 0x7ff583059330>, 'Rarity', '=Inventory!G4', '=Inventory!H4', '={"",H4}']
  - [None, None, <openpyxl.worksheet.formula.ArrayFormula object at 0x7ff582e65d50>, 155.0, None, <openpyxl.worksheet.formula.ArrayFormula object at 0x7ff582e65cf0>, 'Mythic+', '=Inventory!G5', '=Inventory!H5', '={"",H5}']

### Sheet: Tracker
- Dimensions: None rows × None cols
- First non-empty header-like row: 1
- Header values (non-empty): ['Module Tracker (Global stats)', 'Module Tracker (Detailed)', 'Fodder Tracker']
- Formula cells: 584 (scanned 2891 cells)
- Top formulas (up to 10):
  - =IFS(
P5 = "Ancestral 5*", 35,
AND(P5 = "Ancestral 4*",COUNTIF(P6:P9, "Epic+") >= 1),34,
AND(P5 = "Ancestral 4*",Q12 = 17),33,
P5 = "Ancestral 4*",32,
AND(P5 = "Ancestral 3*",COUNTIF(P6:P9, "Epic+") >= 1),31,
AND(P5 = "Ancestral 3*",Q12 = 15),30,
P5 = "Ancestral 3*",29,
AND(P5 = "Ancestral 2*",COUNTIF(P6:P9, "Epic+") >= 1),28,
AND(P5 = "Ancestral 2*",Q12 = 13),27,
P5 = "Ancestral 2*",26,
AND(P5 = "Ancestral 1*",COUNTIF(P6:P9, "Epic+") >= 1),25,
AND(P5 = "Ancestral 1*",Q12 = 11),24,
P5 = "Ancestral 1*",23,
AND(P5 = "Ancestral",COUNTIF(P6:P9, "Epic+") >= 1),22,
AND(P5 = "Ancestral",Q12 = 9),21,
P5 = "Ancestral",20,
AND(P5 = "Mythic+",COUNTIF(P6:P9, "Epic+") >= 2),19,
AND(P5 = "Mythic+",Q12 = 7),18,
AND(P5 = "Mythic+",Q12 = 6),17,
AND(P5 = "Mythic+",Q12 = 5),16,
P5 = "Mythic+",15,
AND(P5 = "Mythic",BD11 >= 1),14,
AND(P5 = "Mythic",SUM($BD5:$BD11) >= 72),13,
P5 = "Mythic",12,
AND(P5 = "Legendary+",BD11 >= 1),11,
AND(P5 = "Legendary+",SUM($BD5:$BD11) >= 72),10,
P5 = "Legendary+", 9,
AND(P5 = "Legendary", OR(P6 = "Epic+", P7 = "Epic+", P8 = "Epic+", P9 = "Epic+")), 8,
AND(P5 = "Legendary",Q12 = 3),7,
P5 = "Legendary", 6,
AND(P5 = "Epic+",BD8 >= 2),5,
AND(P5 = "Epic+",SUM($BD5:$BD11) >= 36),4,
P5 = "Epic+",3,
AND(Q12 = 2,OR(P6 = "Epic", P7 = "Epic", P9 = "Epic", P8 = "Epic")),2,
Q12 = 1,1,
Q12 = 0,0
)
/35 (count=1)
  - =IFS(
V5 = "Ancestral 5*", 35,
AND(V5 = "Ancestral 4*",COUNTIF(V6:V9, "Epic+") >= 1),34,
AND(V5 = "Ancestral 4*",W12 = 17),33,
V5 = "Ancestral 4*",32,
AND(V5 = "Ancestral 3*",COUNTIF(V6:V9, "Epic+") >= 1),31,
AND(V5 = "Ancestral 3*",W12 = 15),30,
V5 = "Ancestral 3*",29,
AND(V5 = "Ancestral 2*",COUNTIF(V6:V9, "Epic+") >= 1),28,
AND(V5 = "Ancestral 2*",W12 = 13),27,
V5 = "Ancestral 2*",26,
AND(V5 = "Ancestral 1*",COUNTIF(V6:V9, "Epic+") >= 1),25,
AND(V5 = "Ancestral 1*",W12 = 11),24,
V5 = "Ancestral 1*",23,
AND(V5 = "Ancestral",COUNTIF(V6:V9, "Epic+") >= 1),22,
AND(V5 = "Ancestral",W12 = 9),21,
V5 = "Ancestral",20,
AND(V5 = "Mythic+",COUNTIF(V6:V9, "Epic+") >= 2),19,
AND(V5 = "Mythic+",W12 = 7),18,
AND(V5 = "Mythic+",W12 = 6),17,
AND(V5 = "Mythic+",W12 = 5),16,
V5 = "Mythic+",15,
AND(V5 = "Mythic",BK11 >= 1),14,
AND(V5 = "Mythic",SUM($BD5:$BD11) >= 72),13,
V5 = "Mythic",12,
AND(V5 = "Legendary+",BK11 >= 1),11,
AND(V5 = "Legendary+",SUM($BD5:$BD11) >= 72),10,
V5 = "Legendary+", 9,
AND(V5 = "Legendary", OR(V6 = "Epic+", V7 = "Epic+", V8 = "Epic+", V9 = "Epic+")), 8,
AND(V5 = "Legendary",W12 = 3),7,
V5 = "Legendary", 6,
AND(V5 = "Epic+",BK8 >= 2),5,
AND(V5 = "Epic+",SUM($BD5:$BD11) >= 36),4,
V5 = "Epic+",3,
AND(W12 = 2,OR(V6 = "Epic", V7 = "Epic", V9 = "Epic", V8 = "Epic")),2,
W12 = 1,1,
W12 = 0,0
)
/35 (count=1)
  - =IFS(
AB5 = "Ancestral 5*", 35,
AND(AB5 = "Ancestral 4*",COUNTIF(AB6:AB9, "Epic+") >= 1),34,
AND(AB5 = "Ancestral 4*",AC12 = 17),33,
AB5 = "Ancestral 4*",32,
AND(AB5 = "Ancestral 3*",COUNTIF(AB6:AB9, "Epic+") >= 1),31,
AND(AB5 = "Ancestral 3*",AC12 = 15),30,
AB5 = "Ancestral 3*",29,
AND(AB5 = "Ancestral 2*",COUNTIF(AB6:AB9, "Epic+") >= 1),28,
AND(AB5 = "Ancestral 2*",AC12 = 13),27,
AB5 = "Ancestral 2*",26,
AND(AB5 = "Ancestral 1*",COUNTIF(AB6:AB9, "Epic+") >= 1),25,
AND(AB5 = "Ancestral 1*",AC12 = 11),24,
AB5 = "Ancestral 1*",23,
AND(AB5 = "Ancestral",COUNTIF(AB6:AB9, "Epic+") >= 1),22,
AND(AB5 = "Ancestral",AC12 = 9),21,
AB5 = "Ancestral",20,
AND(AB5 = "Mythic+",COUNTIF(AB6:AB9, "Epic+") >= 2),19,
AND(AB5 = "Mythic+",AC12 = 7),18,
AND(AB5 = "Mythic+",AC12 = 6),17,
AND(AB5 = "Mythic+",AC12 = 5),16,
AB5 = "Mythic+",15,
AND(AB5 = "Mythic",BQ11 >= 1),14,
AND(AB5 = "Mythic",SUM($BD5:$BD11) >= 72),13,
AB5 = "Mythic",12,
AND(AB5 = "Legendary+",BQ11 >= 1),11,
AND(AB5 = "Legendary+",SUM($BD5:$BD11) >= 72),10,
AB5 = "Legendary+", 9,
AND(AB5 = "Legendary", OR(AB6 = "Epic+", AB7 = "Epic+", AB8 = "Epic+", AB9 = "Epic+")), 8,
AND(AB5 = "Legendary",AC12 = 3),7,
AB5 = "Legendary", 6,
AND(AB5 = "Epic+",BQ8 >= 2),5,
AND(AB5 = "Epic+",SUM($BD5:$BD11) >= 36),4,
AB5 = "Epic+",3,
AND(AC12 = 2,OR(AB6 = "Epic", AB7 = "Epic", AB9 = "Epic", AB8 = "Epic")),2,
AC12 = 1,1,
AC12 = 0,0
)
/35 (count=1)
  - =IFS(
AH5 = "Ancestral 5*", 35,
AND(AH5 = "Ancestral 4*",COUNTIF(AH6:AH9, "Epic+") >= 1),34,
AND(AH5 = "Ancestral 4*",AI12 = 17),33,
AH5 = "Ancestral 4*",32,
AND(AH5 = "Ancestral 3*",COUNTIF(AH6:AH9, "Epic+") >= 1),31,
AND(AH5 = "Ancestral 3*",AI12 = 15),30,
AH5 = "Ancestral 3*",29,
AND(AH5 = "Ancestral 2*",COUNTIF(AH6:AH9, "Epic+") >= 1),28,
AND(AH5 = "Ancestral 2*",AI12 = 13),27,
AH5 = "Ancestral 2*",26,
AND(AH5 = "Ancestral 1*",COUNTIF(AH6:AH9, "Epic+") >= 1),25,
AND(AH5 = "Ancestral 1*",AI12 = 11),24,
AH5 = "Ancestral 1*",23,
AND(AH5 = "Ancestral",COUNTIF(AH6:AH9, "Epic+") >= 1),22,
AND(AH5 = "Ancestral",AI12 = 9),21,
AH5 = "Ancestral",20,
AND(AH5 = "Mythic+",COUNTIF(AH6:AH9, "Epic+") >= 2),19,
AND(AH5 = "Mythic+",AI12 = 7),18,
AND(AH5 = "Mythic+",AI12 = 6),17,
AND(AH5 = "Mythic+",AI12 = 5),16,
AH5 = "Mythic+",15,
AND(AH5 = "Mythic",BW11 >= 1),14,
AND(AH5 = "Mythic",SUM($BD5:$BD11) >= 72),13,
AH5 = "Mythic",12,
AND(AH5 = "Legendary+",BW11 >= 1),11,
AND(AH5 = "Legendary+",SUM($BD5:$BD11) >= 72),10,
AH5 = "Legendary+", 9,
AND(AH5 = "Legendary", OR(AH6 = "Epic+", AH7 = "Epic+", AH8 = "Epic+", AH9 = "Epic+")), 8,
AND(AH5 = "Legendary",AI12 = 3),7,
AH5 = "Legendary", 6,
AND(AH5 = "Epic+",BW8 >= 2),5,
AND(AH5 = "Epic+",SUM($BD5:$BD11) >= 36),4,
AH5 = "Epic+",3,
AND(AI12 = 2,OR(AH6 = "Epic", AH7 = "Epic", AH9 = "Epic", AH8 = "Epic")),2,
AI12 = 1,1,
AI12 = 0,0
)
/35 (count=1)
  - =IFS(
AN5 = "Ancestral 5*", 35,
AND(AN5 = "Ancestral 4*",COUNTIF(AN6:AN9, "Epic+") >= 1),34,
AND(AN5 = "Ancestral 4*",AO12 = 17),33,
AN5 = "Ancestral 4*",32,
AND(AN5 = "Ancestral 3*",COUNTIF(AN6:AN9, "Epic+") >= 1),31,
AND(AN5 = "Ancestral 3*",AO12 = 15),30,
AN5 = "Ancestral 3*",29,
AND(AN5 = "Ancestral 2*",COUNTIF(AN6:AN9, "Epic+") >= 1),28,
AND(AN5 = "Ancestral 2*",AO12 = 13),27,
AN5 = "Ancestral 2*",26,
AND(AN5 = "Ancestral 1*",COUNTIF(AN6:AN9, "Epic+") >= 1),25,
AND(AN5 = "Ancestral 1*",AO12 = 11),24,
AN5 = "Ancestral 1*",23,
AND(AN5 = "Ancestral",COUNTIF(AN6:AN9, "Epic+") >= 1),22,
AND(AN5 = "Ancestral",AO12 = 9),21,
AN5 = "Ancestral",20,
AND(AN5 = "Mythic+",COUNTIF(AN6:AN9, "Epic+") >= 2),19,
AND(AN5 = "Mythic+",AO12 = 7),18,
AND(AN5 = "Mythic+",AO12 = 6),17,
AND(AN5 = "Mythic+",AO12 = 5),16,
AN5 = "Mythic+",15,
AND(AN5 = "Mythic",CC11 >= 1),14,
AND(AN5 = "Mythic",SUM($BD5:$BD11) >= 72),13,
AN5 = "Mythic",12,
AND(AN5 = "Legendary+",CC11 >= 1),11,
AND(AN5 = "Legendary+",SUM($BD5:$BD11) >= 72),10,
AN5 = "Legendary+", 9,
AND(AN5 = "Legendary", OR(AN6 = "Epic+", AN7 = "Epic+", AN8 = "Epic+", AN9 = "Epic+")), 8,
AND(AN5 = "Legendary",AO12 = 3),7,
AN5 = "Legendary", 6,
AND(AN5 = "Epic+",CC8 >= 2),5,
AND(AN5 = "Epic+",SUM($BD5:$BD11) >= 36),4,
AN5 = "Epic+",3,
AND(AO12 = 2,OR(AN6 = "Epic", AN7 = "Epic", AN9 = "Epic", AN8 = "Epic")),2,
AO12 = 1,1,
AO12 = 0,0
)
/35 (count=1)
  - =IFS(
AT5 = "Ancestral 5*", 35,
AND(AT5 = "Ancestral 4*",COUNTIF(AT6:AT9, "Epic+") >= 1),34,
AND(AT5 = "Ancestral 4*",AU12 = 17),33,
AT5 = "Ancestral 4*",32,
AND(AT5 = "Ancestral 3*",COUNTIF(AT6:AT9, "Epic+") >= 1),31,
AND(AT5 = "Ancestral 3*",AU12 = 15),30,
AT5 = "Ancestral 3*",29,
AND(AT5 = "Ancestral 2*",COUNTIF(AT6:AT9, "Epic+") >= 1),28,
AND(AT5 = "Ancestral 2*",AU12 = 13),27,
AT5 = "Ancestral 2*",26,
AND(AT5 = "Ancestral 1*",COUNTIF(AT6:AT9, "Epic+") >= 1),25,
AND(AT5 = "Ancestral 1*",AU12 = 11),24,
AT5 = "Ancestral 1*",23,
AND(AT5 = "Ancestral",COUNTIF(AT6:AT9, "Epic+") >= 1),22,
AND(AT5 = "Ancestral",AU12 = 9),21,
AT5 = "Ancestral",20,
AND(AT5 = "Mythic+",COUNTIF(AT6:AT9, "Epic+") >= 2),19,
AND(AT5 = "Mythic+",AU12 = 7),18,
AND(AT5 = "Mythic+",AU12 = 6),17,
AND(AT5 = "Mythic+",AU12 = 5),16,
AT5 = "Mythic+",15,
AND(AT5 = "Mythic",CC11 >= 1),14,
AND(AT5 = "Mythic",SUM($BD5:$BD11) >= 72),13,
AT5 = "Mythic",12,
AND(AT5 = "Legendary+",CC11 >= 1),11,
AND(AT5 = "Legendary+",SUM($BD5:$BD11) >= 72),10,
AT5 = "Legendary+", 9,
AND(AT5 = "Legendary", OR(AT6 = "Epic+", AT7 = "Epic+", AT8 = "Epic+", AT9 = "Epic+")), 8,
AND(AT5 = "Legendary",AU12 = 3),7,
AT5 = "Legendary", 6,
AND(AT5 = "Epic+",CC8 >= 2),5,
AND(AT5 = "Epic+",SUM($BD5:$BD11) >= 36),4,
AT5 = "Epic+",3,
AND(AU12 = 2,OR(AT6 = "Epic", AT7 = "Epic", AT9 = "Epic", AT8 = "Epic")),2,
AU12 = 1,1,
AU12 = 0,0
)
/35 (count=1)
  - =IFS(
SUM(R5:R9,X5:X9,AD5:AD9,AJ5:AJ9,AP5:AP9,AV5:AW9)>=1080,"Shatter!",
SUM(R5:R9,X5:X9,AD5:AD9,AJ5:AJ9,AP5:AP9,AV5:AW9)+BD8+BD10>=1080,"Shatter new mods",
BE11>=1080,"Merge, if possible",
TRUE, "Keep farming"
)
&IF(IDS_LAB_LEVEL("Shatter Shards")<5,"*","") (count=1)
  - =Q12 (count=1)
  - =R12 (count=1)
  - =S12 (count=1)
- Preview (first 5 rows × 10 cols):
  - [None, 'Module Tracker (Global stats)', None, None, None, None, None, None, None, None]
  - [None, None, None, None, None, None, None, None, None, None]
  - ['Modules Obtained', 'Cannon Summary', None, None, None, None, None, 'Generator Summary', None, None]
  - [None, 'Mod', 'Qty', '%Can', '%T', 'Progress', None, 'Mod', 'Qty', '%Gen']
  - [None, 'AD', '=Q12', '=R12', '=S12', '=R3', None, 'BHD', '=Q34', '=R34']

### Sheet: Reroll Calculator v3
- Dimensions: None rows × None cols
- First non-empty header-like row: 1
- Header values (non-empty): ['Confidence:', 0.95, 'Desired Effects', 'Locks', 'Epic', 'Legendary', 'Mythic', 'Ancestral', 'By Freeman0916', 'Note: There are slightly lower odds to roll an effect at higher rarities if it can appear at lower rarities due to the fact if it rolls at the lower rarity in an early open slot during a roll, it prevents it from appearing again at the desired higher rarity in the same roll. Because of this, it is more beneficial when banning effects to ban ones that can only appear at a higher rarity that are undesirable. This sheet does not account for this variation yet.']
- Formula cells: 1482 (scanned 2744 cells)
- Top formulas (up to 10):
  - =13-B24 (count=4)
  - =17-B6 (count=3)
  - =26-B34 (count=3)
  - =17-B15 (count=2)
  - =IFERROR(AV13, "-") (count=1)
  - =IFERROR(F4*$D41, "-") (count=1)
  - =IFERROR(AM13, "-") (count=1)
  - =IFERROR(H4*$D41, "-") (count=1)
  - =IFERROR(AD13, "-") (count=1)
  - =IFERROR(J4*$D41, "-") (count=1)
- Preview (first 5 rows × 10 cols):
  - ['Confidence:', 0.95, None, 'Desired Effects', 'Locks', 'Epic', None, 'Legendary', None, 'Mythic']
  - [None, None, None, None, None, 'Max Rolls Needed', 'Dice Needed', 'Max Rolls Needed', 'Dice Needed', 'Max Rolls Needed']
  - [None, None, None, None, None, None, None, None, None, None]
  - ['Cannon (Attack)', None, None, 8.0, 0.0, '=IFERROR(AV13, "-")', '=IFERROR(F4*$D41, "-")', '=IFERROR(AM13, "-")', '=IFERROR(H4*$D41, "-")', '=IFERROR(AD13, "-")']
  - ['Slots Unlocked:', 5.0, None, 7.0, '=E4+1', '=IFERROR(AW13, "-")', '=IFERROR(F5*$D42, "-")', '=IFERROR(AN13, "-")', '=IFERROR(H5*$D42, "-")', '=IFERROR(AE13, "-")']

### Sheet: EXPORT
- Dimensions: None rows × None cols
- First non-empty header-like row: 2
- Header values (non-empty): ['Assist Slot', '=Presets!F2', '=Inventory!D8', 'Assist Slot', '=Presets!F8', '=Inventory!D21', 'Assist Slot', '=Presets!F14', '=Inventory!D34', 'Assist Slot', '=Presets!F20', '=Inventory!D47']
- Formula cells: 85 (scanned 2730 cells)
- Top formulas (up to 10):
  - =Presets!F2 (count=1)
  - =Inventory!D8 (count=1)
  - =Presets!F8 (count=1)
  - =Inventory!D21 (count=1)
  - =Presets!F14 (count=1)
  - =Inventory!D34 (count=1)
  - =Presets!F20 (count=1)
  - =Inventory!D47 (count=1)
  - =Presets!E3 (count=1)
  - =Presets!E9 (count=1)
- Preview (first 5 rows × 10 cols):
  - ['Mv5', None, None, None, None, None, None, None, None, None]
  - [None, 'Assist Slot', '=Presets!F2', '=Inventory!D8', None, None, 'Assist Slot', '=Presets!F8', '=Inventory!D21', None]
  - [None, 'Rarity Cap', '=Presets!E3', None, None, None, 'Rarity Cap', '=Presets!E9', None, None]
  - [None, 'Multiplier Cap', '=Presets!E4', '=Presets!F4', None, None, 'Multiplier Cap', '=Presets!E10', '=Presets!F10', None]
  - [None, 'Substat Cap', '=Presets!E5', '=Presets!F5', None, None, 'Substat Cap', '=Presets!E11', '=Presets!F11', None]
- EXPORT columns (20): ['Mv5', 'Unnamed: 1', 'Unnamed: 2', 'Unnamed: 3', 'Unnamed: 4', 'Unnamed: 5', 'Unnamed: 6', 'Unnamed: 7', 'Unnamed: 8', 'Unnamed: 9', 'Unnamed: 10', 'Unnamed: 11', 'Unnamed: 12', 'Unnamed: 13', 'Unnamed: 14', 'Unnamed: 15', 'Unnamed: 16', 'Unnamed: 17', 'Unnamed: 18', 'Unnamed: 19']
- EXPORT row count: 119

### Sheet: Optimal Assist levels
- Dimensions: None rows × None cols
- First non-empty header-like row: 2
- Header values (non-empty): ['Shard Cost Discount', 'Farming', 'Cannon', 'Armor', 'Generator', 'Core']
- Formula cells: 4388 (scanned 5603 cells)
- Top formulas (up to 10):
  - ='Master Sheet'!C9*1% (count=1)
  - <openpyxl.worksheet.formula.ArrayFormula object at 0x7ff5831f1840> (count=1)
  - <openpyxl.worksheet.formula.ArrayFormula object at 0x7ff5831f2920> (count=1)
  - <openpyxl.worksheet.formula.ArrayFormula object at 0x7ff5831f1cc0> (count=1)
  - <openpyxl.worksheet.formula.ArrayFormula object at 0x7ff5831f03a0> (count=1)
  - =IF(Presets!$E$2="Unlocked",Presets!E4+'Master Sheet'!C16*1%,0%) (count=1)
  - =IF(Presets!$E$8="Unlocked",Presets!E10+'Master Sheet'!C17*1%,0%) (count=1)
  - =IF(Presets!$E$14="Unlocked",Presets!E16+'Master Sheet'!C18*1%,0%) (count=1)
  - =IF(Presets!$E$20="Unlocked",Presets!E22+'Master Sheet'!C19*1%,0%) (count=1)
  - =Inventory!D5 (count=1)
- Preview (first 5 rows × 10 cols):
  - [None, None, None, None, None, None, None, None, None, None]
  - [None, None, 'Shard Cost Discount', None, 'Farming', 'Cannon', 'Armor', 'Generator', 'Core', None]
  - [None, None, "='Master Sheet'!C9*1%", None, 'Max Level', <openpyxl.worksheet.formula.ArrayFormula object at 0x7ff58344dd80>, <openpyxl.worksheet.formula.ArrayFormula object at 0x7ff58344fcd0>, <openpyxl.worksheet.formula.ArrayFormula object at 0x7ff58344e560>, <openpyxl.worksheet.formula.ArrayFormula object at 0x7ff58344ee60>, None]
  - [None, None, None, None, 'Assist %', '=IF(Presets!$E$2="Unlocked",Presets!E4+\'Master Sheet\'!C16*1%,0%)', '=IF(Presets!$E$8="Unlocked",Presets!E10+\'Master Sheet\'!C17*1%,0%)', '=IF(Presets!$E$14="Unlocked",Presets!E16+\'Master Sheet\'!C18*1%,0%)', '=IF(Presets!$E$20="Unlocked",Presets!E22+\'Master Sheet\'!C19*1%,0%)', None]
  - [None, None, None, None, None, None, None, None, None, None]

### Sheet: Shard Path
- Dimensions: None rows × None cols
- First non-empty header-like row: 3
- Header values (non-empty): ['Common Drop Chance', '↓ Shard Lab PATH  ↓', 'The Effective Avg. Shard Lab Path (0.27.0) (Time focused)', 'Total Lab Time', 'User Specific Guess', 'Formulas', 'Lab', 'Workshop ($)', 'LAB PATH UPDATE RUNNING', 'eShard Calculations', 'eShard Simulations', 'TIME USAGE vs eSHARD GAIN', 'LAB PATH UPDATE MATRIX']
- Formula cells: 4415 (scanned 9750 cells)
- Top formulas (up to 10):
  - =X8 (count=2)
  - =0.4%*(X11+1) (count=2)
  - =IFERROR(__xludf.DUMMYFUNCTION("IF(F6="""",""🎉 eShard Labs are complete 🎉"", SPARKLINE(AQ5:AQ35))"),"") (count=1)
  - =FORMAT_TIME_YEAR(SUM(D6:D150)) (count=1)
  - =RIGHT($L$5,LEN($L$5)-1) (count=1)
  - ='Master Sheet'!C5 (count=1)
  - =IDS_LAB_TARGET(W5) (count=1)
  - =X5*0.2% (count=1)
  - =MAX('_IDS'!G49:H49) (count=1)
  - =6%+0.4%*AB5 (count=1)
- Preview (first 5 rows × 10 cols):
  - [None, None, None, None, None, None, None, None, None, None]
  - [None, None, None, None, None, '=IFERROR(__xludf.DUMMYFUNCTION("IF(F6="""",""🎉 eShard Labs are complete 🎉"", SPARKLINE(AQ5:AQ35))"),"")', None, None, None, None]
  - [None, None, 'Common Drop Chance', None, '↓ Shard Lab PATH  ↓', 'The Effective Avg. Shard Lab Path (0.27.0) (Time focused)', None, None, None, None]
  - [None, None, 'Daily Mission Shards', None, None, 'Lab', 'Level', 'Cost', 'Duration', 'ROI / day']
  - [None, None, 'Rare Drop Chance', '=RIGHT($L$5,LEN($L$5)-1)', None, None, None, None, None, None]

### Sheet: Overview
- Dimensions: None rows × None cols
- First non-empty header-like row: 5
- Header values (non-empty): ['Effect', 'Epic', 'Legendary', 'Mythic', 'Ancestral', 'Effect', 'Epic', 'Legendary', 'Mythic', 'Ancestral']
- Formula cells: 0 (scanned 357 cells)
- Preview (first 5 rows × 10 cols):
  - [None, None, None, None, None, None, None, None, None, None]
  - [None, 'The Tower Modules, v27', None, None, None, None, None, None, None, None]
  - [None, None, None, None, None, None, None, None, None, None]
  - [None, 'Cannon Modules', None, None, None, None, None, None, None, 'Generator Modules']
  - [None, None, None, 'Effect', 'Epic', 'Legendary', 'Mythic', 'Ancestral', None, None]

### Sheet: Substats
- Dimensions: None rows × None cols
- First non-empty header-like row: 6
- Header values (non-empty): ['Attack Speed', '=MOD_SUBSTAT_LOOKUP(B6,"common",1)', '=MOD_SUBSTAT_LOOKUP(B6,"rare",1)', '=MOD_SUBSTAT_LOOKUP(B6,"epic",1)', '=MOD_SUBSTAT_LOOKUP(B6,"legendary",1)', '=MOD_SUBSTAT_LOOKUP(B6,"mythic",1)', '=MOD_SUBSTAT_LOOKUP(B6,"ancestral",1)', 'Cash Bonus', '=MOD_SUBSTAT_LOOKUP(J6,"common",1)', '=MOD_SUBSTAT_LOOKUP(J6,"rare",1)', '=MOD_SUBSTAT_LOOKUP(J6,"epic",1)', '=MOD_SUBSTAT_LOOKUP(J6,"legendary",1)', '=MOD_SUBSTAT_LOOKUP(J6,"mythic",1)', '=MOD_SUBSTAT_LOOKUP(J6,"ancestral",1)']
- Formula cells: 438 (scanned 936 cells)
- Top formulas (up to 10):
  - =MOD_SUBSTAT_LOOKUP(B6,"common",1) (count=1)
  - =MOD_SUBSTAT_LOOKUP(B6,"rare",1) (count=1)
  - =MOD_SUBSTAT_LOOKUP(B6,"epic",1) (count=1)
  - =MOD_SUBSTAT_LOOKUP(B6,"legendary",1) (count=1)
  - =MOD_SUBSTAT_LOOKUP(B6,"mythic",1) (count=1)
  - =MOD_SUBSTAT_LOOKUP(B6,"ancestral",1) (count=1)
  - =MOD_SUBSTAT_LOOKUP(J6,"common",1) (count=1)
  - =MOD_SUBSTAT_LOOKUP(J6,"rare",1) (count=1)
  - =MOD_SUBSTAT_LOOKUP(J6,"epic",1) (count=1)
  - =MOD_SUBSTAT_LOOKUP(J6,"legendary",1) (count=1)
- Preview (first 5 rows × 10 cols):
  - [None, None, None, None, None, None, None, None, None, None]
  - [None, 'The Tower Module Substats, v27', None, None, None, None, None, None, None, None]
  - [None, None, None, None, None, None, None, None, None, 'by Kosmirion Epos / kosmirionepos\nDonations Welcome: 335558378DD4C132']
  - [None, None, None, None, None, None, None, None, None, None]
  - [None, 'Cannon Module', None, None, None, None, None, None, None, 'Generator Module']

### Sheet: Module Costs
- Dimensions: None rows × None cols
- First non-empty header-like row: 2
- Header values (non-empty): ['Module Level', 'Shards', 'Shard cost', '(Cummulated)', 'Coin cost', 'Coin cost', '(Cummulated)']
- Formula cells: 2100 (scanned 2718 cells)
- Top formulas (up to 10):
  - =1 (count=1)
  - =DVT_MODULE_SHARDS_COST(B3) (count=1)
  - =FORMAT_NUMBER(C3) (count=1)
  - =FORMAT_NUMBER(SUM(C$3:C3)) (count=1)
  - =DVT_MODULE_COINS_COST(B3) (count=1)
  - =FORMAT_NUMBER(F3) (count=1)
  - =FORMAT_NUMBER(SUM(F$3:F3)) (count=1)
  - =1+B3 (count=1)
  - =DVT_MODULE_SHARDS_COST(B4) (count=1)
  - =FORMAT_NUMBER(C4) (count=1)
- Preview (first 5 rows × 10 cols):
  - [None, None, None, None, None, None, None, None, None, None]
  - [None, 'Module Level', 'Shards', 'Shard cost', '(Cummulated)', 'Coin cost', 'Coin cost', '(Cummulated)', None, None]
  - [None, '=1', '=DVT_MODULE_SHARDS_COST(B3)', '=FORMAT_NUMBER(C3)', '=FORMAT_NUMBER(SUM(C$3:C3))', '=DVT_MODULE_COINS_COST(B3)', '=FORMAT_NUMBER(F3)', '=FORMAT_NUMBER(SUM(F$3:F3))', None, None]
  - [None, '=1+B3', '=DVT_MODULE_SHARDS_COST(B4)', '=FORMAT_NUMBER(C4)', '=FORMAT_NUMBER(SUM(C$3:C4))', '=DVT_MODULE_COINS_COST(B4)', '=FORMAT_NUMBER(F4)', '=FORMAT_NUMBER(SUM(F$3:F4))', None, None]
  - [None, '=1+B4', '=DVT_MODULE_SHARDS_COST(B5)', '=FORMAT_NUMBER(C5)', '=FORMAT_NUMBER(SUM(C$3:C5))', '=DVT_MODULE_COINS_COST(B5)', '=FORMAT_NUMBER(F5)', '=FORMAT_NUMBER(SUM(F$3:F5))', None, None]

### Sheet: DVT_Laboratory
- Dimensions: None rows × None cols
- First non-empty header-like row: 1
- Header values (non-empty): ['=IFERROR(__xludf.DUMMYFUNCTION("IMPORTRANGE(""165-JujisYPpKi3RWew9O5gptDJ6rgr-71BbyoQafoaU"", ""DVT_Laboratory!A1:ZZ103"")"),"")', '=IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),"Game Speed")', '=IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),"Starting Cash")', '=IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),"Workshop Attack Discount")', '=IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),"Workshop Defense Discount")', '=IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),"Workshop Utility Discount")', '=IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),"Labs Coin Discount")', '=IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),"Labs Speed")', '=IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),"Buy Multiplier")', '=IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),"More Round Stats")', '=IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),"Target Priority")', '=IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),"Card Presets")', '=IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),"Workshop Respec")', '=IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),"Reroll Daily Mission")', '=IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),"Workshop Enhancements")', '=IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),"Enhancement Attack - Coin Discount")', '=IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),"Enhancement Defense - Coin Discount")', '=IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),"Enhancement Utility - Coin Discount")', '=IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),"Damage")', '=IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),"Attack Speed")', '=IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),"Critical Factor")', '=IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),"Range")', '=IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),"Damage / Meter")', '=IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),"Super Crit Chance")', '=IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),"Super Crit Multi")', '=IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),"Max Rend Armor Multiplier")', '=IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),"Light Speed Shots")', '=IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),"Health")', '=IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),"Health Regen")', '=IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),"Defense Absolute")', '=IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),"Defense %")', '=IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),"Orbs Speed")', '=IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),"Land Mine Damage")', '=IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),"Land Mine Decay")', '=IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),"Shockwave Size")', '=IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),"Orb Boss Hit")', '=IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),"Wall Health")', '=IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),"Wall Rebuild")', '=IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),"Wall Regen")', '=IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),"Wall Thorns")', '=IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),"Wall Invincibility")', '=IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),"Wall Fortification")', '=IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),"Garlic Thorns")', '=IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),"Cash Bonus")', '=IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),"Cash / Wave")', '=IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),"Coins / Kill Bonus")', '=IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),"Coins / Wave")', '=IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),"Interest")', '=IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),"Max Interest")', '=IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),"Package After Boss")', '=IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),"Recovery Package Amount")', '=IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),"Recovery Package Max")', '=IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),"Recovery Package Chance")', '=IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),"Enemy Attack Level Skip")', '=IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),"Enemy Health Level Skip")', '=IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),"Missile Despawn Time")', '=IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),"Missiles Explosion")', '=IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),"Missile Radius")', '=IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),"Chrono Field Duration")', '=IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),"Chrono Field Damage Reduction")', '=IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),"Chrono Field Reduction %")', '=IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),"Swamp Radius")', '=IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),"Swamp Stun")', '=IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),"Swamp Stun Chance")', '=IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),"Swamp Stun Time")', '=IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),"Golden Tower Bonus")', '=IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),"Golden Tower Duration")', '=IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),"Chain Lightning Shock")', '=IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),"Shock Chance")', '=IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),"Shock Multiplier")', '=IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),"Death Wave Health")', '=IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),"Death Wave Coin bonus")', '=IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),"Inner Mine Blast Radius")', '=IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),"Inner Mine Rotation Speed")', '=IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),"Chrono Field Range")', '=IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),"Missile Amplifier")', '=IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),"Missile Barrage")', '=IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),"Missile Barrage Quantity")', '=IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),"Inner Mine Stun")', '=IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),"Black Hole Damage")', '=IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),"Extra Black Hole")', '=IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),"Black Hole Coin Bonus")', '=IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),"Spotlight Coin Bonus")', '=IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),"Spotlight Missiles")', '=IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),"Black Hole Disable Ranged Enemies")', '=IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),"Recharge Missile Barrage")', '=IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),"Swamp Rend")', '=IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),"Swamp Rend - Additional Enemies")', '=IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),"Chain Thunder")', '=IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),"Lightning Amplifier - Scatter")', '=IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),"Death Wave Cells Bonus")', '=IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),"Death Wave Damage Amplifier")', '=IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),"Death Wave Armor Stripping")', '=IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),"Inner Land Mine - Chrono Jump")', '=IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),"Second Wind Blast")', '=IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),"Double Death Ray")', '=IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),"Extra Orb Adjuster")', '=IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),"Extra Extra Orbs")', '=IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),"Energy Shield Extra Hit")', '=IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),"Super Tower Bonus")', '=IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),"Recharge Second Wind")', '=IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),"Recharge Demon Mode")', '=IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),"Recharge Nuke")', '=IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),"Card Mastery")', '=IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),"Unlock Perks")', '=IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),"Waves Required")', '=IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),"Auto Pick Perks")', '=IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),"Standard Perks Bonus")', '=IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),"Perk Option Quantity")', '=IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),"First Perk Choice")', '=IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),"Ban Perks")', '=IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),"Improve Trade-off Perks")', '=IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),"Auto Pick Ranking")', '=IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),"Flame Bot - Cooldown")', '=IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),"Thunder Bot - Cooldown")', '=IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),"Gold Bot - Cooldown")', '=IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),"Amp Bot - Cooldown")', '=IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),"Flame Bot - Burn Stack")', '=IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),"Thunder Bot - Linger Time")', '=IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),"Gold Bot - Duration")', '=IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),"Amp Bot - Duration")', '=IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),"Common Enemy Health")', '=IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),"Common Enemy Attack")', '=IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),"Fast Enemy Health")', '=IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),"Fast Enemy Attack")', '=IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),"Fast Enemy Speed")', '=IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),"Tank Enemy Health")', '=IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),"Tank Enemy Attack")', '=IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),"Ranged Enemy Health")', '=IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),"Ranged Enemy Attack")', '=IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),"Boss Health")', '=IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),"Boss Attack")', '=IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),"Protector Health")', '=IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),"Protector Radius")', '=IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),"Protector Damage Reduction")', '=IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),"Ray Enemy Attack")', '=IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),"Ray Enemy Health")', '=IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),"Vampire Enemy Attack")', '=IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),"Vampire Enemy Health")', '=IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),"Scatter Enemy Attack")', '=IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),"Scatter Enemy Health")', '=IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),"Ranged Enemy Range")', '=IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),"Common Drop Chance")', '=IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),"Reroll Shards")', '=IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),"Daily Mission shards")', '=IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),"Module Shards Cost")', '=IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),"Module Coin Cost")', '=IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),"Rare Drop Chance")', '=IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),"Unmerge Module")', '=IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),"Shatter Shards")', '=IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),"Cannon Effect Bans")', '=IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),"Armor Effect Bans")', '=IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),"Generator Effect Bans")', '=IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),"Core Effect Bans")', '=IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),"Assist Module Substats - Cannon")', '=IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),"Assist Module Substats - Armor")', '=IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),"Assist Module Substats - Generator")', '=IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),"Assist Module Substats - Core")', '=IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),"Assist Module Bonus - Cannon")', '=IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),"Assist Module Bonus - Armor")', '=IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),"Assist Module Bonus - Generator")', '=IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),"Assist Module Bonus - Core")', '=IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),"Battle Condition Reduction")', '=IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),"Knockback Resistance")', '=IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),"Thorns Resistance")', '=IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),"Orb Resistance")', '=IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),"Plasma Cannon Resistance")', '=IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),"Death Ray Resistance")', '=IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),"Armored Enemies")', '=IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),"Enemy Speed")', '=IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),"More Enemies")', '=IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),"Enemy Attack Speed")', '=IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),"Fast\'s Ultimate")', '=IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),"Ranged Ultimate")', '=IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),"Boss\'s Ultimate")', '=IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),"Basic\'s Ultimate")', '=IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),"Tank\'s Ultimate")', '=IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),"Protector\'s Ultimate")', '=IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),"Ultimate Weapon Durations ")', '=IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),"Death Defy Down")', '=IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),"Energy Shields Down")', '=IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),"Enemy Level Skip Reduction")']
- Formula cells: 9001 (scanned 20000 cells - truncated)
- Top formulas (up to 10):
  - =IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),"Duration") (count=181)
  - =IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),"Cost") (count=181)
  - =IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),1.0E18) (count=29)
  - =IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),1.5E18) (count=24)
  - =IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),53.99722222222222) (count=23)
  - =IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),161.9923611111111) (count=23)
  - =IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),2.0E18) (count=22)
  - =IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),32.39791666666667) (count=22)
  - =IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),4.0E18) (count=22)
  - =IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),2.25E18) (count=20)
- Preview (first 5 rows × 10 cols):
  - ['=IFERROR(__xludf.DUMMYFUNCTION("IMPORTRANGE(""165-JujisYPpKi3RWew9O5gptDJ6rgr-71BbyoQafoaU"", ""DVT_Laboratory!A1:ZZ103"")"),"")', '=IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),"Game Speed")', None, '=IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),"Starting Cash")', None, '=IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),"Workshop Attack Discount")', None, '=IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),"Workshop Defense Discount")', None, '=IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),"Workshop Utility Discount")']
  - ['=IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),"Lvl")', '=IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),"Duration")', '=IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),"Cost")', '=IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),"Duration")', '=IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),"Cost")', '=IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),"Duration")', '=IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),"Cost")', '=IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),"Duration")', '=IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),"Cost")', '=IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),"Duration")']
  - ['=IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),1.0)', '=IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),0.0069328703703703705)', '=IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),300.0)', '=IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),1.6203703703703703E-4)', '=IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),30.0)', '=IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),1.6203703703703703E-4)', '=IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),30.0)', '=IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),1.6203703703703703E-4)', '=IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),30.0)', '=IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),1.6203703703703703E-4)']
  - ['=IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),2.0)', '=IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),0.10347222222222222)', '=IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),2500.0)', '=IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),0.0044444444444444444)', '=IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),71.0)', '=IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),0.0044444444444444444)', '=IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),71.0)', '=IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),0.0044444444444444444)', '=IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),71.0)', '=IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),0.0044444444444444444)']
  - ['=IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),3.0)', '=IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),0.41597222222222224)', '=IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),12000.0)', '=IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),0.01138888888888889)', '=IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),178.0)', '=IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),0.01138888888888889)', '=IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),178.0)', '=IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),0.01138888888888889)', '=IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),178.0)', '=IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),0.01138888888888889)']

## Copy of Player & Stuff v3.5.2.xlsx
- Size: 619515 bytes
- Sheets: Home Page, IDS, _IDS, Master Sheet, Perk PWR, Milestone Rewards, Milestone Earnings, WS Mastery, Fleets Rewards Calculator, Enemies Immunities, Enemies Drop, Battle Conditions, Elite Spawn, Fleet Spawn, DVT_PlayerAndStuff, EXPORT

### Sheet: Home Page
- Dimensions: None rows × None cols
- First non-empty header-like row: 4
- Header values (non-empty): ['=HYPERLINK("https://docs.google.com/spreadsheets/d/1kExWaxZpSizb0KPoFtZdGZI0iBOszTG0LwK-248Saak/copy", "Player & Stuff Initial Link")', 'Sheet Tab', 'Creator', 'Main Contributor', 'Helpers']
- Formula cells: 7 (scanned 429 cells)
- Top formulas (up to 10):
  - =HYPERLINK("https://docs.google.com/spreadsheets/d/1kExWaxZpSizb0KPoFtZdGZI0iBOszTG0LwK-248Saak/copy", "Player & Stuff Initial Link") (count=1)
  - =IFERROR(__xludf.DUMMYFUNCTION("IMPORTRANGE(""1kExWaxZpSizb0KPoFtZdGZI0iBOszTG0LwK-248Saak"", ""'Home Page'!B12:C13"")"),"v3.5.2") (count=1)
  - =IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),"feat: Including ESm in Enemies Immunities") (count=1)
  - =IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),"v3.5.1") (count=1)
  - =IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),"fix: only count UW perks if they are unlocked") (count=1)
  - =IFERROR(__xludf.DUMMYFUNCTION("IMPORTRANGE(""1eCPPuQOE3Pyh8HhnApEMK3RFIutkUjWd61ppVImwWk8"", ""_Giveaway_summary!A1:A2"")"),"⚠️ 2 Giveaway(s) running - 2 Feb | 5 Feb") (count=1)
  - =IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),"Giveaway Details") (count=1)
- Preview (first 5 rows × 10 cols):
  - [None, None, None, None, None, None, None, None, None, None]
  - [None, 'Player & Stuff', None, None, None, None, None, None, None, None]
  - [None, None, None, None, None, None, None, None, None, None]
  - [None, '=HYPERLINK("https://docs.google.com/spreadsheets/d/1kExWaxZpSizb0KPoFtZdGZI0iBOszTG0LwK-248Saak/copy", "Player & Stuff Initial Link")', None, None, None, None, 'Sheet Tab', 'Creator', 'Main Contributor', 'Helpers']
  - [None, None, None, None, None, None, None, None, None, None]

### Sheet: IDS
- Dimensions: None rows × None cols
- First non-empty header-like row: 6
- Header values (non-empty): ["IDS Master's ID       ➡️", '18XbHJtHzu8tjqnP_9JcsZFA6jIwjOKRYmzBzOYBMv2I', '=IFERROR(__xludf.DUMMYFUNCTION("IFERROR(C6.url, IFS(LEFT(C6,8)=""https://"", C6, LEN(C6)=44, ""https://docs.google.com/spreadsheets/d/"" & C6 & ""/edit"", TRUE, C6))"),"https://docs.google.com/spreadsheets/d/18XbHJtHzu8tjqnP_9JcsZFA6jIwjOKRYmzBzOYBMv2I/edit")', '=IFERROR(__xludf.DUMMYFUNCTION("IF(D6<>"""", IF(IMPORTRANGE(D6,""EXPORT!A1"") = F6, ""✅"", ""Wrong ID or Version""), """")"),"✅")', 'v2']
- Formula cells: 4 (scanned 268 cells)
- Top formulas (up to 10):
  - =IFERROR(__xludf.DUMMYFUNCTION("IFERROR(C6.url, IFS(LEFT(C6,8)=""https://"", C6, LEN(C6)=44, ""https://docs.google.com/spreadsheets/d/"" & C6 & ""/edit"", TRUE, C6))"),"https://docs.google.com/spreadsheets/d/18XbHJtHzu8tjqnP_9JcsZFA6jIwjOKRYmzBzOYBMv2I/edit") (count=1)
  - =IFERROR(__xludf.DUMMYFUNCTION("IF(D6<>"""", IF(IMPORTRANGE(D6,""EXPORT!A1"") = F6, ""✅"", ""Wrong ID or Version""), """")"),"✅") (count=1)
  - =HYPERLINK("https://docs.google.com/spreadsheets/d/1osjoqKmMwtOWs7Up3e21-3ofN1RHOjsgKV6y3dc6rgE/copy", "1️⃣ Copy Me") (count=1)
  - =IFS(
  ISERROR(E6), "3️⃣ Click on #REF! and then AUTHORISE ↗",
  E6="", "2️⃣ Please input your IDS Master's ID here ⤴️",
  E6="✅", HYPERLINK(D6, "Go to my IDS Master Sheet"),
  TRUE, "") (count=1)
- Preview (first 5 rows × 10 cols):
  - [None, None, None, None, None, None, None, None, None, None]
  - [None, 'The IDS System', None, None, None, None, None, None, 'Looking for the Import script ? Just run it as you were doing it before, but from IDS Master.\nIt will let you import every new versions at once!', None]
  - [None, None, None, None, None, None, None, None, None, None]
  - [None, 'This Sheet ID is :', '1fjJxEFt9ZZ5og_q7xHZuyRTf3p_OOUNwCXVV6VtGof0', None, None, None, None, None, None, None]
  - [None, None, None, None, None, None, None, None, None, None]

### Sheet: _IDS
- Dimensions: None rows × None cols
- First non-empty header-like row: 1
- Header values (non-empty): ['=IFERROR(__xludf.DUMMYFUNCTION("IMPORTRANGE(IF(IDS!E6=""✅"", IDS!D6, ""1osjoqKmMwtOWs7Up3e21-3ofN1RHOjsgKV6y3dc6rgE""), ""_IDS!A1:CE212"")"),"Labs")', '=IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),"https://docs.google.com/spreadsheets/d/1yLi6Ni4nZr0Wfct7MmbyNRRi5v6fR62t0kdI-g8NeNo/edit")', '=IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),"✅")', '=IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),"v2.3.2")', '=IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),"WS")', '=IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),"https://docs.google.com/spreadsheets/d/1462mmIeTEmChEYwwpDWacv611QCRW9n-Dvz8oyOQ798/edit")', '=IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),"✅")', '=IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),"v2.2.8")', '=IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),"WS+")', '=IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),"UWs")', '=IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),"https://docs.google.com/spreadsheets/d/1aLEWX2qblJJt96I6QduS_Fp2DjMO6rNToPrUBWGI5BU/edit")', '=IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),"✅")', '=IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),"v2.1.2")', '=IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),"Cards")', '=IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),"https://docs.google.com/spreadsheets/d/1HMQwNLTvcw7aXmjjL7cXmZSdjAF_62ehWpwDIdjqEGs/edit")', '=IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),"✅")', '=IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),"Cards Presets")', '=IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),"v2.2.3")', '=IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),"Relics")', '=IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),"https://docs.google.com/spreadsheets/d/1jtZ_RhMszIY0NzPm-kNhYg_w5D8WDm9tXSJatvVpWDU/edit")', '=IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),"✅")', '=IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),"Vault")', '=IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),"")', '=IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),"Bots")', '=IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),"https://docs.google.com/spreadsheets/d/1gopHNYu4SgI0UbRvscCV4_C1gct7FXr5GBBcjCzCxC0/edit")', '=IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),"✅")', '=IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),"v2.2")', '=IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),"Themes & Songs")', '=IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),"https://docs.google.com/spreadsheets/d/1umYUbdc7TGYJhqFv662Yol9PGzfECdpLYxl4ElV6UwQ/edit")', '=IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),"✅")', '=IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),"Modules")', '=IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),"https://docs.google.com/spreadsheets/d/1mz0hSpsng0Kzlz8xk0VEyRgaE62Gzj5kNLu3Vp-4gGE/edit")', '=IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),"✅")', '=IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),"v5.12")', '=IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),"Guardians")', '=IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),"https://docs.google.com/spreadsheets/d/19vecjglXSr9t51C6vJy-lMGk1xH4h52ytBr-uyKxLcM/edit")', '=IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),"✅")', '=IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),"v2.2.5")', '=IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),"Player & Stuff")', '=IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),"https://docs.google.com/spreadsheets/d/1fjJxEFt9ZZ5og_q7xHZuyRTf3p_OOUNwCXVV6VtGof0/edit")', '=IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),"✅")', '=IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),"v3.5.2")']
- Formula cells: 2561 (scanned 20000 cells - truncated)
- Top formulas (up to 10):
  - =IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),"") (count=186)
  - =IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),0.0) (count=173)
  - =IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),99.0) (count=59)
  - =IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),FALSE) (count=55)
  - =IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),20.0) (count=50)
  - =IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),30.0) (count=49)
  - =IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),7.0) (count=46)
  - =IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),TRUE) (count=45)
  - =IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),1.0) (count=45)
  - =IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),"Stat") (count=33)
- Preview (first 5 rows × 10 cols):
  - ['=IFERROR(__xludf.DUMMYFUNCTION("IMPORTRANGE(IF(IDS!E6=""✅"", IDS!D6, ""1osjoqKmMwtOWs7Up3e21-3ofN1RHOjsgKV6y3dc6rgE""), ""_IDS!A1:CE212"")"),"Labs")', '=IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),"https://docs.google.com/spreadsheets/d/1yLi6Ni4nZr0Wfct7MmbyNRRi5v6fR62t0kdI-g8NeNo/edit")', '=IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),"✅")', '=IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),"v2.3.2")', '=IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),"WS")', '=IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),"https://docs.google.com/spreadsheets/d/1462mmIeTEmChEYwwpDWacv611QCRW9n-Dvz8oyOQ798/edit")', '=IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),"✅")', '=IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),"v2.2.8")', None, None]
  - ['=IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),"Game Speed")', '=IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),7.0)', '=IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),7.0)', '=IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),7.0)', '=IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),"U")', '=IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),"Workshop Upgrade")', '=IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),"Farming")', None, '=IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),"Tourney")', None]
  - ['=IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),"Starting Cash")', '=IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),6.0)', None, '=IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),99.0)', None, None, '=IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),"¢ Level")', '=IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),"$ Level")', '=IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),"¢ Level")', '=IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),"$ Level")']
  - ['=IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),"Workshop Attack Discount")', '=IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),16.0)', None, '=IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),99.0)', None, '=IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),"Damage")', '=IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),5750.0)', '=IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),6000.0)', '=IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),5750.0)', '=IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),6000.0)']
  - ['=IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),"Workshop Defense Discount")', '=IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),19.0)', None, '=IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),99.0)', None, '=IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),"Attack Speed")', '=IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),99.0)', '=IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),99.0)', '=IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),99.0)', '=IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),99.0)']

### Sheet: Master Sheet
- Dimensions: None rows × None cols
- First non-empty header-like row: 1
- Header values (non-empty): ['Stat', 'Value', 'Tier', 'Wave', 'P', 'Run date', 'Labs', 'Level', 'Max', '=IF(\'_IDS\'!AS1="✅", HYPERLINK(\'_IDS\'!AR1, "Go to my Modules Sheet"), "Module")', 'Substat', 'Rarity', 'Value']
- Formula cells: 44 (scanned 693 cells)
- Top formulas (up to 10):
  - =IF('_IDS'!AS1="✅", HYPERLINK('_IDS'!AR1, "Go to my Modules Sheet"), "Module") (count=1)
  - =IDS_LAB_LEVEL(J2) (count=1)
  - =IDS_MOD_GENERATOR_SUBSTATS(P5) (count=1)
  - =IDS_LAB_LEVEL(J3) (count=1)
  - =IDS_LAB_LEVEL(J4) (count=1)
  - =IDS_LAB_LEVEL(J5) (count=1)
  - =IDS_MOD_GENERATOR_NAME(P2) (count=1)
  - =IDS_LAB_LEVEL(J6) (count=1)
  - =IDS_MOD_GENERATOR_RARITY(P5) (count=1)
  - =IDS_LAB_LEVEL(J7) (count=1)
- Preview (first 5 rows × 10 cols):
  - [None, 'Stat', 'Value', None, 'Tier', 'Wave', 'P', 'Run date', None, 'Labs']
  - ['PLAYER STATS', 'Player ID', '4C64DCF66976FD33', 'MILESTONES', 'Tier 1', 10210.0, True, None, 'OTHER - Labs, WS, Cards', 'Game Speed']
  - [None, 'Farming Tier', 'Tier 14', None, 'Tier 2', 5628.0, None, None, None, 'Package after Boss']
  - [None, 'Tourney League', 'Legends', None, 'Tier 3', 5402.0, None, None, None, 'Recovery Package Chance']
  - [None, 'Lifetime Coins', 3570000000000.0, None, 'Tier 4', 6310.0, True, None, None, 'Death Wave Cells Bonus']

### Sheet: Perk PWR
- Dimensions: None rows × None cols
- First non-empty header-like row: 2
- Header values (non-empty): ['Perk #', 'Base Wave', 'With \nWaves Required\nLab Reduction', 'With 1 Perk Wave\nRequirement\nreduction perk', 'With 2 Perk Wave\nRequirement\nreduction perks', 'With 3 Perk Wave\nRequirement\nreduction perks']
- Formula cells: 343 (scanned 1148 cells)
- Top formulas (up to 10):
  - =F3-($C$4*E3) (count=1)
  - =G3 (count=1)
  - =H3 (count=1)
  - =I3 (count=1)
  - ='Master Sheet'!K9 (count=1)
  - =F4-($C$4*E4) (count=1)
  - =floor($G$3*(1-(20*(1+($C$5/100))/100)),1)*E4 (count=1)
  - =H4 (count=1)
  - =I4 (count=1)
  - ='Master Sheet'!K10 (count=1)
- Preview (first 5 rows × 10 cols):
  - [None, None, None, None, None, None, None, None, None, None]
  - [None, None, None, None, 'Perk #', 'Base Wave', 'With \nWaves Required\nLab Reduction', 'With 1 Perk Wave\nRequirement\nreduction perk', 'With 2 Perk Wave\nRequirement\nreduction perks', 'With 3 Perk Wave\nRequirement\nreduction perks']
  - [None, 'Target Wave', 750.0, None, 1.0, 200.0, '=F3-($C$4*E3)', '=G3', '=H3', '=I3']
  - [None, 'Waves Required Lab Value', "='Master Sheet'!K9", None, 2.0, 400.0, '=F4-($C$4*E4)', '=floor($G$3*(1-(20*(1+($C$5/100))/100)),1)*E4', '=H4', '=I4']
  - [None, 'Standard Perks Bonus Lab', "='Master Sheet'!K10", None, 3.0, 600.0, '=F5-($C$4*E5)', '=floor($G$3*(1-(20*(1+($C$5/100))/100)),1)*E5', '=floor($G$3*(1-(40*(1+($C$5/100))/100)),1)*E5', '=I5']

### Sheet: Milestone Rewards
- Dimensions: None rows × None cols
- First non-empty header-like row: 1
- Header values (non-empty): ['↓ Milestone Pass 1 ↓', 'Tier 1', 'Tier 2', 'Tier 3', '↓ Milestone Pass 2 ↓', 'Tier 4', 'Tier 5', 'Tier 6', '↓ Milestone Pass 3 ↓', 'Tier 7', 'Tier 8', 'Tier 9', '↓ Milestone Pass 4 ↓', 'Tier 10', 'Tier 11', 'Tier 12', '↓ Milestone Pass 5 ↓', 'Tier 13', 'Tier 14', 'Tier 15', '↓ Milestone Pass 6 ↓', 'Tier 16', 'Tier 17', 'Tier 18', '↓ Milestone Pass 7 ↓', 'Tier 19', 'Tier 20', 'Tier 21']
- Formula cells: 714 (scanned 3230 cells)
- Top formulas (up to 10):
  - ='Milestone Earnings'!M4 (count=3)
  - ='Milestone Earnings'!M7 (count=3)
  - ='Milestone Earnings'!M10 (count=3)
  - ='Milestone Earnings'!M13 (count=3)
  - ='Milestone Earnings'!M16 (count=3)
  - ='Milestone Earnings'!M19 (count=3)
  - ='Milestone Earnings'!M22 (count=3)
  - =sumif(C$12:C$34,$A2,D$12:D$34) (count=1)
  - =IF(C2>0, FORMAT_NUMBER(C2), "") (count=1)
  - =sumif(E$12:E$34,$A2,F$12:F$34) (count=1)
- Preview (first 5 rows × 10 cols):
  - [None, '↓ Milestone Pass 1 ↓', 'Tier 1', None, None, None, 'Tier 2', None, None, None]
  - ['coins', None, '=sumif(C$12:C$34,$A2,D$12:D$34)', '=IF(C2>0, FORMAT_NUMBER(C2), "")', '=sumif(E$12:E$34,$A2,F$12:F$34)', '=FORMAT_NUMBER(E2)', '=sumif(G$12:G$34,$A2,H$12:H$34)', '=IF(G2>0, FORMAT_NUMBER(G2), "")', '=sumif(I$12:I$34,$A2,J$12:J$34)', '=FORMAT_NUMBER(I2)']
  - ['gems', None, '=sumif(C$12:C$34,$A3,D$12:D$34)', '=FORMAT_NUMBER(C3)', '=sumif(E$12:E$34,$A3,F$12:F$34)', '=FORMAT_NUMBER(E3)', '=sumif(G$12:G$34,$A3,H$12:H$34)', '=FORMAT_NUMBER(G3)', '=sumif(I$12:I$34,$A3,J$12:J$34)', '=FORMAT_NUMBER(I3)']
  - ['stones', None, '=sumif(C$12:C$34,$A4,D$12:D$34)', '=FORMAT_NUMBER(C4) & " ⧌"', '=sumif(E$12:E$34,$A4,F$12:F$34)', '=FORMAT_NUMBER(E4) & " ⧌"', '=sumif(G$12:G$34,$A4,H$12:H$34)', '=FORMAT_NUMBER(G4) & " ⧌"', '=sumif(I$12:I$34,$A4,J$12:J$34)', '=FORMAT_NUMBER(I4) & " ⧌"']
  - ['unlock', None, '=COUNTIF(C$12:C$34,$A5)', '=IF(C5>0, C5,"")', '=COUNTIF(E$12:E$34,$A5)', '=IF(E5>0, E5,"")', '=COUNTIF(G$12:G$34,$A5)', '=IF(G5>0, G5,"")', '=COUNTIF(I$12:I$34,$A5)', '=IF(I5>0, I5,"")']

### Sheet: Milestone Earnings
- Dimensions: None rows × None cols
- First non-empty header-like row: 3
- Header values (non-empty): ['Wave', 'Owned', 'Remains', 'Coins', 'Owned', 'Remains', 'Gems', 'Owned', 'Remains', 'Stones', 'Owned', 'Remains', 'Coins', 'Owned', 'Remains', 'Gems', 'Owned', 'Remains', 'Stones', 'Pack Price', 'Current ROI', 'Final ROI', 'Packs', 'Ressources', 'Final ROI']
- Formula cells: 479 (scanned 780 cells)
- Top formulas (up to 10):
  - =IFERROR(__xludf.DUMMYFUNCTION("MAX(FILTER({0, 10,20,30,40,50,60,70,80,90,100,150,200,250,300,400,500,750,1000,1250,1500,2000,2500,4500}, {0, 10,20,30,40,50,60,70,80,90,100,150,200,250,300,400,500,750,1000,1250,1500,2000,2500,4500} <= 'Master Sheet'!F2))
"),4500.0) (count=1)
  - =SUMIFS('Milestone Rewards'!D12:D34,'Milestone Rewards'!C12:C34,$F$3,'Milestone Rewards'!$A12:$A34,"<="&C4) (count=1)
  - =SUMIFS('Milestone Rewards'!D12:D34,'Milestone Rewards'!C12:C34,$F$3,'Milestone Rewards'!$A12:$A34,">"&C4) (count=1)
  - =FORMAT_NUMBER(D4)&" / "&FORMAT_NUMBER(D4+E4) (count=1)
  - =SUMIFS('Milestone Rewards'!D12:D34,'Milestone Rewards'!C12:C34,$I$3,'Milestone Rewards'!$A12:$A34,"<="&C4) (count=1)
  - =SUMIFS('Milestone Rewards'!D12:D34,'Milestone Rewards'!C12:C34,$I$3,'Milestone Rewards'!$A12:$A34,">"&C4) (count=1)
  - =FORMAT_NUMBER(G4)&" / "&FORMAT_NUMBER(G4+H4) (count=1)
  - =SUMIFS('Milestone Rewards'!D12:D34,'Milestone Rewards'!C12:C34,$L$3,'Milestone Rewards'!$A12:$A34,"<="&C4) (count=1)
  - =SUMIFS('Milestone Rewards'!D12:D34,'Milestone Rewards'!C12:C34,$L$3,'Milestone Rewards'!$A12:$A34,">"&C4) (count=1)
  - =FORMAT_NUMBER(J4)&" / "&FORMAT_NUMBER(J4+K4) (count=1)
- Preview (first 5 rows × 10 cols):
  - [None, None, None, None, None, None, None, None, None, None]
  - [None, None, 'Standard', None, None, None, None, None, None, None]
  - [None, None, 'Wave', 'Owned', 'Remains', 'Coins', 'Owned', 'Remains', 'Gems', 'Owned']
  - [None, 'Tier 1', '=IFERROR(__xludf.DUMMYFUNCTION("MAX(FILTER({0, 10,20,30,40,50,60,70,80,90,100,150,200,250,300,400,500,750,1000,1250,1500,2000,2500,4500}, {0, 10,20,30,40,50,60,70,80,90,100,150,200,250,300,400,500,750,1000,1250,1500,2000,2500,4500} <= \'Master Sheet\'!F2))\n"),4500.0)', '=SUMIFS(\'Milestone Rewards\'!D12:D34,\'Milestone Rewards\'!C12:C34,$F$3,\'Milestone Rewards\'!$A12:$A34,"<="&C4)', '=SUMIFS(\'Milestone Rewards\'!D12:D34,\'Milestone Rewards\'!C12:C34,$F$3,\'Milestone Rewards\'!$A12:$A34,">"&C4)', '=FORMAT_NUMBER(D4)&" / "&FORMAT_NUMBER(D4+E4)', '=SUMIFS(\'Milestone Rewards\'!D12:D34,\'Milestone Rewards\'!C12:C34,$I$3,\'Milestone Rewards\'!$A12:$A34,"<="&C4)', '=SUMIFS(\'Milestone Rewards\'!D12:D34,\'Milestone Rewards\'!C12:C34,$I$3,\'Milestone Rewards\'!$A12:$A34,">"&C4)', '=FORMAT_NUMBER(G4)&" / "&FORMAT_NUMBER(G4+H4)', '=SUMIFS(\'Milestone Rewards\'!D12:D34,\'Milestone Rewards\'!C12:C34,$L$3,\'Milestone Rewards\'!$A12:$A34,"<="&C4)']
  - [None, 'Tier 2', '=IFERROR(__xludf.DUMMYFUNCTION("MAX(FILTER({0, 10,20,30,40,50,60,70,80,90,100,150,200,250,300,400,500,750,1000,1250,1500,2000,2500,4500}, {0, 10,20,30,40,50,60,70,80,90,100,150,200,250,300,400,500,750,1000,1250,1500,2000,2500,4500} <= \'Master Sheet\'!F3))\n"),4500.0)', '=SUMIFS(\'Milestone Rewards\'!H12:H34,\'Milestone Rewards\'!G12:G34,$F$3,\'Milestone Rewards\'!$A12:$A34,"<="&C5)', '=SUMIFS(\'Milestone Rewards\'!H12:H34,\'Milestone Rewards\'!G12:G34,$F$3,\'Milestone Rewards\'!$A12:$A34,">"&C5)', '=FORMAT_NUMBER(D5)&" / "&FORMAT_NUMBER(D5+E5)', '=SUMIFS(\'Milestone Rewards\'!H12:H34,\'Milestone Rewards\'!G12:G34,$I$3,\'Milestone Rewards\'!$A12:$A34,"<="&C5)', '=SUMIFS(\'Milestone Rewards\'!H12:H34,\'Milestone Rewards\'!G12:G34,$I$3,\'Milestone Rewards\'!$A12:$A34,">"&C5)', '=FORMAT_NUMBER(G5)&" / "&FORMAT_NUMBER(G5+H5)', '=SUMIFS(\'Milestone Rewards\'!H12:H34,\'Milestone Rewards\'!G12:G34,$L$3,\'Milestone Rewards\'!$A12:$A34,"<="&C5)']

### Sheet: WS Mastery
- Dimensions: None rows × None cols
- First non-empty header-like row: 5
- Header values (non-empty): ['=SWITCH(B3, "Locked", "9%", 1, "9%", 2, "10%", 3, "11%", 4, "13%", 5, "15%", 6, "17%", 7, "19%", "9%")', 0.0, 0.1, 0.15, 0.2, 0.25, 0.3, 0.35, 0.4, 0.45, 0.5, 0.55, 'Credits']
- Formula cells: 212 (scanned 504 cells)
- Top formulas (up to 10):
  - ='Master Sheet'!K16 (count=1)
  - =IF('Master Sheet'!L16, "Lvl "&'Master Sheet'!K6, "No Mast.") (count=1)
  - =SWITCH(B3, "Locked", "9%", 1, "9%", 2, "10%", 3, "11%", 4, "13%", 5, "15%", 6, "17%", 7, "19%", "9%") (count=1)
  - =$B$5-SUM(C8:C22) (count=1)
  - =$B$5-SUM(D8:D22) (count=1)
  - =$B$5-SUM(E8:E22) (count=1)
  - =$B$5-SUM(F8:F22) (count=1)
  - =$B$5-SUM(G8:G22) (count=1)
  - =$B$5-SUM(H8:H22) (count=1)
  - =$B$5-SUM(I8:I22) (count=1)
- Preview (first 5 rows × 10 cols):
  - [None, None, None, None, None, None, None, None, None, None]
  - [None, 'Wave Skip Level', None, 'Wave Skip Mastery', None, None, None, None, None, None]
  - [None, "='Master Sheet'!K16", None, '=IF(\'Master Sheet\'!L16, "Lvl "&\'Master Sheet\'!K6, "No Mast.")', None, None, None, None, None, None]
  - [None, None, None, None, None, None, None, None, None, None]
  - [None, '=SWITCH(B3, "Locked", "9%", 1, "9%", 2, "10%", 3, "11%", 4, "13%", 5, "15%", 6, "17%", 7, "19%", "9%")', 0.0, 0.1, 0.15, 0.2, 0.25, 0.3, 0.35, 0.4]

### Sheet: Fleets Rewards Calculator
- Dimensions: None rows × None cols
- First non-empty header-like row: 2
- Header values (non-empty): ['Best Tier', 'Estimated daily shards', 'Should you use IS?', 'Seconds per day', 'Intro sprint seconds', 'Seconds per wave', 'Wave count', "='Fleets Rewards Calculator'!C7", "='Fleets Rewards Calculator'!C8", "='Fleets Rewards Calculator'!C9", "='Fleets Rewards Calculator'!C10", "='Fleets Rewards Calculator'!C11", "='Fleets Rewards Calculator'!C12", "='Fleets Rewards Calculator'!C13", "='Fleets Rewards Calculator'!C14"]
- Formula cells: 203 (scanned 1021 cells)
- Top formulas (up to 10):
  - ='Fleets Rewards Calculator'!C7 (count=1)
  - ='Fleets Rewards Calculator'!C8 (count=1)
  - ='Fleets Rewards Calculator'!C9 (count=1)
  - ='Fleets Rewards Calculator'!C10 (count=1)
  - ='Fleets Rewards Calculator'!C11 (count=1)
  - ='Fleets Rewards Calculator'!C12 (count=1)
  - ='Fleets Rewards Calculator'!C13 (count=1)
  - ='Fleets Rewards Calculator'!C14 (count=1)
  - <openpyxl.worksheet.formula.ArrayFormula object at 0x7ff583190190> (count=1)
  - =MAX(F7:G14) (count=1)
- Preview (first 5 rows × 10 cols):
  - [None, None, None, None, None, None, None, None, None, None]
  - [None, None, 'Best Tier', 'Estimated daily shards', None, 'Should you use IS?', None, None, None, 'Seconds per day']
  - [None, None, <openpyxl.worksheet.formula.ArrayFormula object at 0x7ff583191510>, '=MAX(F7:G14)', None, '=if(isnumber(XMATCH(D3,F7:F14)),"Yes","No")', None, None, None, 86400.0]
  - [None, None, 'SHARD DROPS', None, None, None, None, None, 'Intro Sprint', None]
  - [None, None, None, 'Per Run', None, 'Per Day', None, None, 'Waves skipped', 'Waves double skipped']

### Sheet: Enemies Immunities
- Dimensions: None rows × None cols
- First non-empty header-like row: 2
- Header values (non-empty): ['Fast Ult.', 'Tank Ult.', 'Range Ult.', 'Boss &\nBoss Ult.', 'Protector', 'Prot. Ult.', 'Elites &\nElites Ult.', 'Fleets']
- Formula cells: 0 (scanned 360 cells)
- Preview (first 5 rows × 10 cols):
  - [None, None, None, None, None, None, None, None, None, None]
  - [None, None, None, 'Fast Ult.', 'Tank Ult.', 'Range Ult.', 'Boss &\nBoss Ult.', 'Protector', 'Prot. Ult.', 'Elites &\nElites Ult.']
  - [None, 'Slow', 'Slow', None, None, None, None, None, 'Immune', None]
  - [None, None, 'Thunderbot', None, None, None, '50% Slow', None, None, '50% Slow']
  - [None, 'Stuns', 'Thunderbot', None, None, None, None, None, 'Immune', None]

### Sheet: Enemies Drop
- Dimensions: None rows × None cols
- First non-empty header-like row: 2
- Header values (non-empty): ['Basic', 'Fast', 'Tanks', 'Ranged', 'Boss', 'Protectors', 'Elites', 'Fleets']
- Formula cells: 0 (scanned 108 cells)
- Preview (first 5 rows × 10 cols):
  - [None, None, None, None, None, None, None, None, None, None]
  - [None, None, None, 'Basic', 'Fast', 'Tanks', 'Ranged', 'Boss', 'Protectors', 'Elites']
  - [None, None, 'Coins', 'x1 with Crit Coin', 'x2', 'x4', 'x2', 'x5', 'x3', 'x4']
  - [None, 'Modules', 'Common', None, None, None, None, 'Up to 3%', None, None]
  - [None, None, 'Rare', None, None, None, None, 'Up to 1.5%', None, None]

### Sheet: Battle Conditions
- Dimensions: None rows × None cols
- First non-empty header-like row: 2
- Header values (non-empty): ['Armored Enemies', 'Basic Ultimate - Chance to upgrade Basic Enemies', 'Boss Ultimate', 'Death Defy Down', 'Death Ray Resistance', 'Enemy Attack Speed', 'Energy Shields Down', 'Enemy Speed', 'Fast Ultimate', 'More Bosses', 'More Enemies', 'Knockback Resistance', 'Orb Resistance', 'Plasma Cannon Resistance', "Protector's Ultimate", 'Ranged Ultimate (Tower Disable Time)', "Tank's Ultimate", 'Thorns Resistance', 'Ultimate Weapons Duration', 'Enemy Level Skip 📗']
- Formula cells: 0 (scanned 598 cells)
- Preview (first 5 rows × 10 cols):
  - ['Wave', 'Battle Conditions', None, None, None, None, None, None, None, None]
  - [None, 'Armored Enemies', 'Basic Ultimate - Chance to upgrade Basic Enemies', None, None, None, None, 'Boss Ultimate', 'Death Defy Down', 'Death Ray Resistance']
  - [None, None, 'Fast', 'Tank', 'Range', 'Boss', 'Protector', None, None, None]
  - [0.0, 1.0, 0.01, 0.01, 0.01, 0.01, 0.01, 0.05, -0.01, 0.9]
  - [20.0, 2.0, 0.01, 0.01, 0.01, 0.01, 0.01, 0.1, -0.02, 0.8]

### Sheet: Elite Spawn
- Dimensions: None rows × None cols
- First non-empty header-like row: 3
- Header values (non-empty): ['Cells average:', 1.0, 1.5, 2.0, 2.5, 3.0, 3.5, 4.0, 4.5, 5.0, 5.5, 6.0, 6.5, 7.0, 10.5, 13.0, 14.0, 14.5, 15.0, 15.5, 16.0, 16.5]
- Formula cells: 398 (scanned 624 cells)
- Top formulas (up to 10):
  - =C5/3 (count=1)
  - =$E5*POW(0.9, F$4-1) (count=1)
  - =$E5*POW(0.9, G$4-1) (count=1)
  - =$E5*POW(0.9, H$4-1) (count=1)
  - =$E5*POW(0.9, I$4-1) (count=1)
  - =$E5*POW(0.9, J$4-1) (count=1)
  - =$E5*POW(0.9, K$4-1) (count=1)
  - =$E5*POW(0.9, L$4-1) (count=1)
  - =$E5*POW(0.9, M$4-1) (count=1)
  - =$E5*POW(0.9, N$4-1) (count=1)
- Preview (first 5 rows × 10 cols):
  - [None, None, None, None, None, None, None, None, None, None]
  - [None, None, 'Elite Enemy Spawn Chance Increase Per Wave and Tier', None, None, None, None, None, None, None]
  - [None, None, 'Cells average:', None, 1.0, 1.5, 2.0, 2.5, 3.0, 3.5]
  - [None, None, 'Chance of \nany elite', 'Chance of\nspecific elite', 1.0, 2.0, 3.0, 4.0, 5.0, 6.0]
  - [None, 'Single Spawn', 0.01, '=C5/3', 500.0, '=$E5*POW(0.9, F$4-1)', '=$E5*POW(0.9, G$4-1)', '=$E5*POW(0.9, H$4-1)', '=$E5*POW(0.9, I$4-1)', '=$E5*POW(0.9, J$4-1)']

### Sheet: Fleet Spawn
- Dimensions: None rows × None cols
- First non-empty header-like row: 1
- Header values (non-empty): ['T14', 'T14+', 'T15', 'T16', 'T17', 'T18', 'T19', 'T20', 'T21']
- Formula cells: 19059 (scanned 20000 cells - truncated)
- Top formulas (up to 10):
  - =MIN(25, 5+FLOOR(A3/250,1)) (count=1)
  - =IFS(
  $A3<2495,              ,
  MOD($A3-2495, 1000)=0, 1,
  TRUE,                 ) (count=1)
  - =IF(C3, C3*1080*0.8,) (count=1)
  - =IF(COUNTA(D$3:D3)<>0, SUM(D$3:D3), ) (count=1)
  - =IF(C3, C3*$B3*0.2,) (count=1)
  - =IF(COUNTA(F$3:F3)<>0, SUM(F$3:F3), ) (count=1)
  - =IFS(
  $A3<895,              ,
  MOD($A3-895, 30)=0, 1,
  TRUE,                 ) (count=1)
  - =IF(H3, H3*1080*0.8,) (count=1)
  - =IF(COUNTA(I$3:I3)<>0, SUM(I$3:I3), ) (count=1)
  - =IF(H3, H3*$B3*0.2,) (count=1)
- Preview (first 5 rows × 10 cols):
  - [None, None, 'T14', None, None, None, None, 'T14+', None, None]
  - ['Wave', 'drops \nper fleet', 'Fleets \nCount', 'Dice', 'Dice sum', 'Shards per wave', 'Shards sum', 'Fleets \nCount', 'Dice', 'Dice sum']
  - [5.0, '=MIN(25, 5+FLOOR(A3/250,1))', '=IFS(\n  $A3<2495,              ,\n  MOD($A3-2495, 1000)=0, 1,\n  TRUE,                 )', '=IF(C3, C3*1080*0.8,)', '=IF(COUNTA(D$3:D3)<>0, SUM(D$3:D3), )', '=IF(C3, C3*$B3*0.2,)', '=IF(COUNTA(F$3:F3)<>0, SUM(F$3:F3), )', '=IFS(\n  $A3<895,              ,\n  MOD($A3-895, 30)=0, 1,\n  TRUE,                 )', '=IF(H3, H3*1080*0.8,)', '=IF(COUNTA(I$3:I3)<>0, SUM(I$3:I3), )']
  - ['=A3+10', '=MIN(25, 5+FLOOR(A4/250,1))', '=IFS(\n$A4<2495, ,\nMOD($A4-2495, 1000)=0, 1,\nTRUE, )', '=IF(C4, C4*1080*0.8,)', '=IF(COUNTA(D$3:D4)<>0, SUM(D$3:D4), )', '=IF(C4, C4*$B4*0.2,)', '=IF(COUNTA(F$3:F4)<>0, SUM(F$3:F4), )', '=IFS(\n$A4<895, ,\nMOD($A4-895, 30)=0, 1,\nTRUE, )', '=IF(H4, H4*1080*0.8,)', '=IF(COUNTA(I$3:I4)<>0, SUM(I$3:I4), )']
  - ['=A4+10', '=MIN(25, 5+FLOOR(A5/250,1))', '=IFS(\n$A5<2495, ,\nMOD($A5-2495, 1000)=0, 1,\nTRUE, )', '=IF(C5, C5*1080*0.8,)', '=IF(COUNTA(D$3:D5)<>0, SUM(D$3:D5), )', '=IF(C5, C5*$B5*0.2,)', '=IF(COUNTA(F$3:F5)<>0, SUM(F$3:F5), )', '=IFS(\n$A5<895, ,\nMOD($A5-895, 30)=0, 1,\nTRUE, )', '=IF(H5, H5*1080*0.8,)', '=IF(COUNTA(I$3:I5)<>0, SUM(I$3:I5), )']

### Sheet: DVT_PlayerAndStuff
- Dimensions: None rows × None cols
- First non-empty header-like row: 1
- Header values (non-empty): ['Daily Missions Rewards', 'Daily Missions Box Rewards', 'Contribution Rewards']
- Formula cells: 13 (scanned 517 cells)
- Top formulas (up to 10):
  - =DVT_PS_TIER_LIST(false) (count=1)
  - =I3*5 (count=1)
  - =I4*5 (count=1)
  - =I5*5 (count=1)
  - =I6*5 (count=1)
  - =I7*5 (count=1)
  - =I8*5 (count=1)
  - =I9*5 (count=1)
  - =SUM(K3:K9) (count=1)
  - =SUM(L3:L9) (count=1)
- Preview (first 5 rows × 10 cols):
  - [None, None, None, None, 'Daily Missions Rewards', None, None, None, 'Daily Missions Box Rewards', None]
  - ['Tiers', 'Tiers', 'Tiers+', 'Daily Missions', None, 'Coins', 'Shards', 'Gems', 'Box', 'Mission Required']
  - [None, 'Tier 1', 'Tier 1', None, '=DVT_PS_TIER_LIST(false)', 25.0, 0.0, 3.0, 1.0, '=I3*5']
  - [None, 'Tier 2', 'Tier 1+', None, 'Tier 2', 100.0, 3.0, 3.0, 2.0, '=I4*5']
  - [None, 'Tier 3', 'Tier 2', None, 'Tier 3', 1000.0, 5.0, 3.0, 3.0, '=I5*5']

### Sheet: EXPORT
- Dimensions: None rows × None cols
- First non-empty header-like row: 2
- Header values (non-empty): ['Tier', 'Wave', 'P', 'Stat', 'Value']
- Formula cells: 38 (scanned 192 cells)
- Top formulas (up to 10):
  - ='Master Sheet'!F2 (count=1)
  - ='Master Sheet'!G2 (count=1)
  - ='Master Sheet'!C2 (count=1)
  - ='Master Sheet'!F3 (count=1)
  - ='Master Sheet'!C3 (count=1)
  - ='Master Sheet'!F4 (count=1)
  - ='Master Sheet'!C4 (count=1)
  - ='Master Sheet'!F5 (count=1)
  - ='Master Sheet'!G5 (count=1)
  - ='Master Sheet'!C5 (count=1)
- Preview (first 5 rows × 10 cols):
  - ['Pv3', None, None, None, None, None, None, None, None, None]
  - [None, 'Tier', 'Wave', 'P', None, 'Stat', 'Value', None, None, None]
  - [None, 'Tier 1', "='Master Sheet'!F2", "='Master Sheet'!G2", None, 'Player ID', "='Master Sheet'!C2", None, None, None]
  - [None, 'Tier 2', "='Master Sheet'!F3", None, None, 'Farming Tier', "='Master Sheet'!C3", None, None, None]
  - [None, 'Tier 3', "='Master Sheet'!F4", None, None, 'Tourney League', "='Master Sheet'!C4", None, None, None]
- EXPORT columns (7): ['Pv3', 'Unnamed: 1', 'Unnamed: 2', 'Unnamed: 3', 'Unnamed: 4', 'Unnamed: 5', 'Unnamed: 6']
- EXPORT row count: 22

## Copy of Relics v2.2.6.xlsx
- Size: 326617 bytes
- Sheets: Home Page, IDS, _IDS, Relics, EXPORT

### Sheet: Home Page
- Dimensions: None rows × None cols
- First non-empty header-like row: 4
- Header values (non-empty): ['=HYPERLINK("https://docs.google.com/spreadsheets/d/13psLga5xkYIcUiupK9tHmlSsZapFD-IS96aCuUvfjP4/copy", "Relics Initial Link")', 'Sheet Tab', 'Main Contributor', 'Helpers']
- Formula cells: 7 (scanned 539 cells)
- Top formulas (up to 10):
  - =HYPERLINK("https://docs.google.com/spreadsheets/d/13psLga5xkYIcUiupK9tHmlSsZapFD-IS96aCuUvfjP4/copy", "Relics Initial Link") (count=1)
  - =IFERROR(__xludf.DUMMYFUNCTION("IMPORTRANGE(""13psLga5xkYIcUiupK9tHmlSsZapFD-IS96aCuUvfjP4"", ""'Home Page'!B12:C13"")"),"v2.2.6") (count=1)
  - =IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),"New relics - Aurora (III)") (count=1)
  - =IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),"v2.2.5") (count=1)
  - =IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),"New relics - Amusement Park") (count=1)
  - =IFERROR(__xludf.DUMMYFUNCTION("IMPORTRANGE(""1eCPPuQOE3Pyh8HhnApEMK3RFIutkUjWd61ppVImwWk8"", ""_Giveaway_summary!A1:A2"")"),"⚠️ 2 Giveaway(s) running - 2 Feb | 5 Feb") (count=1)
  - =IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),"Giveaway Details") (count=1)
- Preview (first 5 rows × 10 cols):
  - [None, None, None, None, None, None, None, None, None, None]
  - [None, 'Relics', None, None, None, None, None, None, None, None]
  - [None, None, None, None, None, None, None, None, None, None]
  - [None, '=HYPERLINK("https://docs.google.com/spreadsheets/d/13psLga5xkYIcUiupK9tHmlSsZapFD-IS96aCuUvfjP4/copy", "Relics Initial Link")', None, None, None, None, 'Sheet Tab', 'Main Contributor', 'Helpers', None]
  - [None, None, None, None, None, None, None, None, None, None]

### Sheet: IDS
- Dimensions: None rows × None cols
- First non-empty header-like row: 6
- Header values (non-empty): ["IDS Master's ID       ➡️", '18XbHJtHzu8tjqnP_9JcsZFA6jIwjOKRYmzBzOYBMv2I', '=IFERROR(__xludf.DUMMYFUNCTION("IFERROR(C6.url, IFS(LEFT(C6,8)=""https://"", C6, LEN(C6)=44, ""https://docs.google.com/spreadsheets/d/"" & C6 & ""/edit"", TRUE, C6))"),"https://docs.google.com/spreadsheets/d/18XbHJtHzu8tjqnP_9JcsZFA6jIwjOKRYmzBzOYBMv2I/edit")', '=IFERROR(__xludf.DUMMYFUNCTION("IF(D6<>"""", IF(IMPORTRANGE(D6,""EXPORT!A1"") = F6, ""✅"", ""Wrong ID or Version""), """")"),"✅")', 'v2']
- Formula cells: 4 (scanned 268 cells)
- Top formulas (up to 10):
  - =IFERROR(__xludf.DUMMYFUNCTION("IFERROR(C6.url, IFS(LEFT(C6,8)=""https://"", C6, LEN(C6)=44, ""https://docs.google.com/spreadsheets/d/"" & C6 & ""/edit"", TRUE, C6))"),"https://docs.google.com/spreadsheets/d/18XbHJtHzu8tjqnP_9JcsZFA6jIwjOKRYmzBzOYBMv2I/edit") (count=1)
  - =IFERROR(__xludf.DUMMYFUNCTION("IF(D6<>"""", IF(IMPORTRANGE(D6,""EXPORT!A1"") = F6, ""✅"", ""Wrong ID or Version""), """")"),"✅") (count=1)
  - =HYPERLINK("https://docs.google.com/spreadsheets/d/1osjoqKmMwtOWs7Up3e21-3ofN1RHOjsgKV6y3dc6rgE/copy", "1️⃣ Copy Me") (count=1)
  - =IFS(
  ISERROR(E6), "3️⃣ Click on #REF! and then AUTHORISE ↗",
  E6="", "2️⃣ Please input your IDS Master's ID here ⤴️",
  E6="✅", HYPERLINK(D6, "Go to my IDS Master Sheet"),
  TRUE, "") (count=1)
- Preview (first 5 rows × 10 cols):
  - [None, None, None, None, None, None, None, None, None, None]
  - [None, 'The IDS System', None, None, None, None, None, None, 'Looking for the Import script ? Just run it as you were doing it before, but from IDS Master.\nIt will let you import every new versions at once!', None]
  - [None, None, None, None, None, None, None, None, None, None]
  - [None, 'This Sheet ID is :', '1jtZ_RhMszIY0NzPm-kNhYg_w5D8WDm9tXSJatvVpWDU', None, None, None, None, None, None, None]
  - [None, None, None, None, None, None, None, None, None, None]

### Sheet: _IDS
- Dimensions: None rows × None cols
- First non-empty header-like row: 1
- Header values (non-empty): ['=IFERROR(__xludf.DUMMYFUNCTION("IMPORTRANGE(IF(IDS!E6=""✅"", IDS!D6, ""1osjoqKmMwtOWs7Up3e21-3ofN1RHOjsgKV6y3dc6rgE""), ""_IDS!A1:BY212"")"),"Labs")', '=IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),"https://docs.google.com/spreadsheets/d/1yLi6Ni4nZr0Wfct7MmbyNRRi5v6fR62t0kdI-g8NeNo/edit")', '=IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),"✅")', '=IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),"v2.3.2")', '=IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),"WS")', '=IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),"https://docs.google.com/spreadsheets/d/1462mmIeTEmChEYwwpDWacv611QCRW9n-Dvz8oyOQ798/edit")', '=IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),"✅")', '=IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),"v2.2.8")', '=IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),"WS+")', '=IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),"UWs")', '=IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),"https://docs.google.com/spreadsheets/d/1aLEWX2qblJJt96I6QduS_Fp2DjMO6rNToPrUBWGI5BU/edit")', '=IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),"✅")', '=IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),"v2.1.2")', '=IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),"Cards")', '=IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),"https://docs.google.com/spreadsheets/d/1HMQwNLTvcw7aXmjjL7cXmZSdjAF_62ehWpwDIdjqEGs/edit")', '=IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),"✅")', '=IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),"Cards Presets")', '=IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),"v2.2.3")', '=IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),"Relics")', '=IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),"https://docs.google.com/spreadsheets/d/1jtZ_RhMszIY0NzPm-kNhYg_w5D8WDm9tXSJatvVpWDU/edit")', '=IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),"✅")', '=IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),"Vault")', '=IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),"")', '=IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),"Bots")', '=IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),"https://docs.google.com/spreadsheets/d/1gopHNYu4SgI0UbRvscCV4_C1gct7FXr5GBBcjCzCxC0/edit")', '=IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),"✅")', '=IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),"v2.2")', '=IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),"Themes & Songs")', '=IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),"https://docs.google.com/spreadsheets/d/1umYUbdc7TGYJhqFv662Yol9PGzfECdpLYxl4ElV6UwQ/edit")', '=IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),"✅")', '=IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),"Modules")', '=IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),"https://docs.google.com/spreadsheets/d/1mz0hSpsng0Kzlz8xk0VEyRgaE62Gzj5kNLu3Vp-4gGE/edit")', '=IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),"✅")', '=IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),"v5.12")', '=IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),"Guardians")', '=IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),"https://docs.google.com/spreadsheets/d/19vecjglXSr9t51C6vJy-lMGk1xH4h52ytBr-uyKxLcM/edit")', '=IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),"✅")', '=IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),"v2.2.5")']
- Formula cells: 2481 (scanned 20000 cells - truncated)
- Top formulas (up to 10):
  - =IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),"") (count=186)
  - =IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),0.0) (count=171)
  - =IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),99.0) (count=59)
  - =IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),FALSE) (count=54)
  - =IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),20.0) (count=50)
  - =IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),30.0) (count=49)
  - =IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),7.0) (count=46)
  - =IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),1.0) (count=45)
  - =IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),TRUE) (count=36)
  - =IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),9.0) (count=33)
- Preview (first 5 rows × 10 cols):
  - ['=IFERROR(__xludf.DUMMYFUNCTION("IMPORTRANGE(IF(IDS!E6=""✅"", IDS!D6, ""1osjoqKmMwtOWs7Up3e21-3ofN1RHOjsgKV6y3dc6rgE""), ""_IDS!A1:BY212"")"),"Labs")', '=IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),"https://docs.google.com/spreadsheets/d/1yLi6Ni4nZr0Wfct7MmbyNRRi5v6fR62t0kdI-g8NeNo/edit")', '=IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),"✅")', '=IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),"v2.3.2")', '=IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),"WS")', '=IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),"https://docs.google.com/spreadsheets/d/1462mmIeTEmChEYwwpDWacv611QCRW9n-Dvz8oyOQ798/edit")', '=IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),"✅")', '=IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),"v2.2.8")', None, None]
  - ['=IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),"Game Speed")', '=IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),7.0)', '=IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),7.0)', '=IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),7.0)', '=IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),"U")', '=IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),"Workshop Upgrade")', '=IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),"Farming")', None, '=IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),"Tourney")', None]
  - ['=IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),"Starting Cash")', '=IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),6.0)', None, '=IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),99.0)', None, None, '=IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),"¢ Level")', '=IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),"$ Level")', '=IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),"¢ Level")', '=IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),"$ Level")']
  - ['=IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),"Workshop Attack Discount")', '=IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),16.0)', None, '=IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),99.0)', None, '=IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),"Damage")', '=IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),5750.0)', '=IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),6000.0)', '=IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),5750.0)', '=IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),6000.0)']
  - ['=IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),"Workshop Defense Discount")', '=IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),19.0)', None, '=IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),99.0)', None, '=IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),"Attack Speed")', '=IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),99.0)', '=IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),99.0)', '=IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),99.0)', '=IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),99.0)']

### Sheet: Relics
- Dimensions: None rows × None cols
- First non-empty header-like row: 2
- Header values (non-empty): ['Rarity', '#', 'Relic Name', 'Bonus Type', 'Value', 'Unlocked', 'Event', 'Unlocked by', 'Type', 'Last seen', 'Total Bonuses', 'Active', 'Total', 'Standard', 'Premium', 'Effective Boost per new Relic']
- Formula cells: 199 (scanned 5954 cells)
- Top formulas (up to 10):
  - =IFERROR(__xludf.DUMMYFUNCTION("FILTER($M$3:$M35, NOT(REGEXMATCH($M$3:$M35, ""^Misc.$|^Defense$|^Utility$|Damage‎ $|Relics"")))"),"Lab Speed") (count=1)
  - =SUMIFS($F:$F,$E:$E,M4,$G:$G,True) (count=1)
  - =SUM(Q4:R4) (count=1)
  - =SUMIFS($F:$F, $E:$E, $M4, $J:$J, "<>Premium") (count=1)
  - =SUMIFS($F:$F, $E:$E, $M4, $J:$J, "=Premium") (count=1)
  - ="+"&ROUND(((1+$N4+T4)/(1+$N4)-1)*100, 1)&"%" (count=1)
  - ="+"&ROUND(((1+$N4+V4)/(1+$N4)-1)*100, 1)&"%" (count=1)
  - =IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),"Bot Range") (count=1)
  - =SUMIFS($F:$F,$E:$E,M5,$G:$G,True) (count=1)
  - =SUM(Q5:R5) (count=1)
- Preview (first 5 rows × 10 cols):
  - [None, None, None, None, None, None, None, None, None, None]
  - [None, 'Rarity', '#', 'Relic Name', 'Bonus Type', 'Value', 'Unlocked', 'Event', 'Unlocked by', 'Type']
  - [None, '1-Rare', 1.0, 'No Spoon', 'Defense Absolute', 0.02, False, 'Matrix', 'Earn 350 medals Matrix event', 'Standard']
  - [None, '1-Rare', 2.0, 'Copper Badge', 'Damage', 0.03, True, None, 'Finish P4 in Copper', 'Tournament']
  - [None, '1-Rare', 3.0, 'Silver Badge', 'Coins', 0.05, True, None, 'Finish P4 in Silver', 'Tournament']

### Sheet: EXPORT
- Dimensions: None rows × None cols
- First non-empty header-like row: 2
- Header values (non-empty): ['Relics', 'Owned', 'TOTAL']
- Formula cells: 60 (scanned 234 cells)
- Top formulas (up to 10):
  - =Relics!N36 (count=1)
  - =Relics!P36 (count=1)
  - =Relics!N37 (count=1)
  - =Relics!P37 (count=1)
  - =C6-C3-C4 (count=1)
  - =Relics!P38 (count=1)
  - =Relics!N41 (count=1)
  - =Relics!P41 (count=1)
  - =Relics!N4 (count=1)
  - =Relics!P4 (count=1)
- Preview (first 5 rows × 10 cols):
  - ['Rv2', None, None, None, None, None, None, None, None, None]
  - [None, 'Relics', 'Owned', None, 'TOTAL', None, None, None, None, None]
  - [None, 'Event Relics', '=Relics!N36', None, '=Relics!P36', None, None, None, None, None]
  - [None, 'Guild Relics', '=Relics!N37', None, '=Relics!P37', None, None, None, None, None]
  - [None, 'Other Relics', '=C6-C3-C4', None, '=Relics!P38', None, None, None, None, None]
- EXPORT columns (5): ['Rv2', 'Unnamed: 1', 'Unnamed: 2', 'Unnamed: 3', 'Unnamed: 4']
- EXPORT row count: 37

## Copy of Themes & Songs v2.1.13.xlsx
- Size: 645099 bytes
- Sheets: Home Page, IDS, _IDS, Themes & Songs, Events Timeline, EXPORT, Giveaways

### Sheet: Home Page
- Dimensions: None rows × None cols
- First non-empty header-like row: 4
- Header values (non-empty): ['=HYPERLINK("https://docs.google.com/spreadsheets/d/1I890hoosDHS0WGwvGpfMTSmlChEFcjvts9seiEygCbQ/copy", "Themes & Songs Initial Link")', 'Sheet Tab', 'Main Contributor', 'Helpers']
- Formula cells: 7 (scanned 473 cells)
- Top formulas (up to 10):
  - =HYPERLINK("https://docs.google.com/spreadsheets/d/1I890hoosDHS0WGwvGpfMTSmlChEFcjvts9seiEygCbQ/copy", "Themes & Songs Initial Link") (count=1)
  - =IFERROR(__xludf.DUMMYFUNCTION("IMPORTRANGE(""1I890hoosDHS0WGwvGpfMTSmlChEFcjvts9seiEygCbQ"", ""'Home Page'!B12:C13"")"),"v2.1.13") (count=1)
  - =IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),"Amusement Park") (count=1)
  - =IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),"v2.1.12") (count=1)
  - =IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),"Snowstorm (II) & Season 6") (count=1)
  - =IFERROR(__xludf.DUMMYFUNCTION("IMPORTRANGE(""1eCPPuQOE3Pyh8HhnApEMK3RFIutkUjWd61ppVImwWk8"", ""_Giveaway_summary!A1:A2"")"),"⚠️ 2 Giveaway(s) running - 2 Feb | 5 Feb") (count=1)
  - =IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),"Giveaway Details") (count=1)
- Preview (first 5 rows × 10 cols):
  - [None, None, None, None, None, None, None, None, None, None]
  - [None, 'Themes & Songs', None, None, None, None, None, None, None, None]
  - [None, None, None, None, None, None, None, None, None, None]
  - [None, '=HYPERLINK("https://docs.google.com/spreadsheets/d/1I890hoosDHS0WGwvGpfMTSmlChEFcjvts9seiEygCbQ/copy", "Themes & Songs Initial Link")', None, None, None, None, 'Sheet Tab', 'Main Contributor', 'Helpers', None]
  - [None, None, None, None, None, None, None, None, None, None]

### Sheet: IDS
- Dimensions: None rows × None cols
- First non-empty header-like row: 6
- Header values (non-empty): ["IDS Master's ID       ➡️", '18XbHJtHzu8tjqnP_9JcsZFA6jIwjOKRYmzBzOYBMv2I', '=IFERROR(__xludf.DUMMYFUNCTION("IFERROR(C6.url, IFS(LEFT(C6,8)=""https://"", C6, LEN(C6)=44, ""https://docs.google.com/spreadsheets/d/"" & C6 & ""/edit"", TRUE, C6))"),"https://docs.google.com/spreadsheets/d/18XbHJtHzu8tjqnP_9JcsZFA6jIwjOKRYmzBzOYBMv2I/edit")', '=IFERROR(__xludf.DUMMYFUNCTION("IF(D6<>"""", IF(IMPORTRANGE(D6,""EXPORT!A1"") = F6, ""✅"", ""Wrong ID or Version""), """")"),"✅")', 'v2']
- Formula cells: 4 (scanned 268 cells)
- Top formulas (up to 10):
  - =IFERROR(__xludf.DUMMYFUNCTION("IFERROR(C6.url, IFS(LEFT(C6,8)=""https://"", C6, LEN(C6)=44, ""https://docs.google.com/spreadsheets/d/"" & C6 & ""/edit"", TRUE, C6))"),"https://docs.google.com/spreadsheets/d/18XbHJtHzu8tjqnP_9JcsZFA6jIwjOKRYmzBzOYBMv2I/edit") (count=1)
  - =IFERROR(__xludf.DUMMYFUNCTION("IF(D6<>"""", IF(IMPORTRANGE(D6,""EXPORT!A1"") = F6, ""✅"", ""Wrong ID or Version""), """")"),"✅") (count=1)
  - =HYPERLINK("https://docs.google.com/spreadsheets/d/1osjoqKmMwtOWs7Up3e21-3ofN1RHOjsgKV6y3dc6rgE/copy", "1️⃣ Copy Me") (count=1)
  - =IFS(
  ISERROR(E6), "3️⃣ Click on #REF! and then AUTHORISE ↗",
  E6="", "2️⃣ Please input your IDS Master's ID here ⤴️",
  E6="✅", HYPERLINK(D6, "Go to my IDS Master Sheet"),
  TRUE, "") (count=1)
- Preview (first 5 rows × 10 cols):
  - [None, None, None, None, None, None, None, None, None, None]
  - [None, 'The IDS System', None, None, None, None, None, None, 'Looking for the Import script ? Just run it as you were doing it before, but from IDS Master.\nIt will let you import every new versions at once!', None]
  - [None, None, None, None, None, None, None, None, None, None]
  - [None, 'This Sheet ID is :', '1umYUbdc7TGYJhqFv662Yol9PGzfECdpLYxl4ElV6UwQ', None, None, None, None, None, None, None]
  - [None, None, None, None, None, None, None, None, None, None]

### Sheet: _IDS
- Dimensions: None rows × None cols
- First non-empty header-like row: 1
- Header values (non-empty): ['=IFERROR(__xludf.DUMMYFUNCTION("IMPORTRANGE(IF(IDS!E6=""✅"", IDS!D6, ""1osjoqKmMwtOWs7Up3e21-3ofN1RHOjsgKV6y3dc6rgE""), ""_IDS!A1:CE245"")"),"Labs")', '=IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),"https://docs.google.com/spreadsheets/d/1yLi6Ni4nZr0Wfct7MmbyNRRi5v6fR62t0kdI-g8NeNo/edit")', '=IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),"✅")', '=IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),"v2.3.2")', '=IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),"WS")', '=IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),"https://docs.google.com/spreadsheets/d/1462mmIeTEmChEYwwpDWacv611QCRW9n-Dvz8oyOQ798/edit")', '=IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),"✅")', '=IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),"v2.2.8")', '=IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),"WS+")', '=IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),"UWs")', '=IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),"https://docs.google.com/spreadsheets/d/1aLEWX2qblJJt96I6QduS_Fp2DjMO6rNToPrUBWGI5BU/edit")', '=IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),"✅")', '=IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),"v2.1.2")', '=IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),"Cards")', '=IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),"https://docs.google.com/spreadsheets/d/1HMQwNLTvcw7aXmjjL7cXmZSdjAF_62ehWpwDIdjqEGs/edit")', '=IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),"✅")', '=IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),"Cards Presets")', '=IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),"v2.2.3")', '=IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),"Relics")', '=IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),"https://docs.google.com/spreadsheets/d/1jtZ_RhMszIY0NzPm-kNhYg_w5D8WDm9tXSJatvVpWDU/edit")', '=IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),"✅")', '=IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),"Vault")', '=IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),"")', '=IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),"Bots")', '=IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),"https://docs.google.com/spreadsheets/d/1gopHNYu4SgI0UbRvscCV4_C1gct7FXr5GBBcjCzCxC0/edit")', '=IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),"✅")', '=IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),"v2.2")', '=IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),"Themes & Songs")', '=IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),"https://docs.google.com/spreadsheets/d/1umYUbdc7TGYJhqFv662Yol9PGzfECdpLYxl4ElV6UwQ/edit")', '=IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),"✅")', '=IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),"Modules")', '=IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),"https://docs.google.com/spreadsheets/d/1mz0hSpsng0Kzlz8xk0VEyRgaE62Gzj5kNLu3Vp-4gGE/edit")', '=IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),"✅")', '=IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),"v5.12")', '=IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),"Guardians")', '=IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),"https://docs.google.com/spreadsheets/d/19vecjglXSr9t51C6vJy-lMGk1xH4h52ytBr-uyKxLcM/edit")', '=IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),"✅")', '=IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),"v2.2.5")', '=IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),"Player & Stuff")', '=IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),"https://docs.google.com/spreadsheets/d/1fjJxEFt9ZZ5og_q7xHZuyRTf3p_OOUNwCXVV6VtGof0/edit")', '=IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),"✅")', '=IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),"v3.5.2")']
- Formula cells: 2564 (scanned 20000 cells - truncated)
- Top formulas (up to 10):
  - =IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),"") (count=186)
  - =IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),0.0) (count=175)
  - =IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),99.0) (count=59)
  - =IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),FALSE) (count=55)
  - =IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),20.0) (count=50)
  - =IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),30.0) (count=49)
  - =IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),7.0) (count=46)
  - =IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),TRUE) (count=45)
  - =IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),1.0) (count=45)
  - =IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),"Stat") (count=33)
- Preview (first 5 rows × 10 cols):
  - ['=IFERROR(__xludf.DUMMYFUNCTION("IMPORTRANGE(IF(IDS!E6=""✅"", IDS!D6, ""1osjoqKmMwtOWs7Up3e21-3ofN1RHOjsgKV6y3dc6rgE""), ""_IDS!A1:CE245"")"),"Labs")', '=IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),"https://docs.google.com/spreadsheets/d/1yLi6Ni4nZr0Wfct7MmbyNRRi5v6fR62t0kdI-g8NeNo/edit")', '=IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),"✅")', '=IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),"v2.3.2")', '=IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),"WS")', '=IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),"https://docs.google.com/spreadsheets/d/1462mmIeTEmChEYwwpDWacv611QCRW9n-Dvz8oyOQ798/edit")', '=IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),"✅")', '=IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),"v2.2.8")', None, None]
  - ['=IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),"Game Speed")', '=IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),7.0)', '=IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),7.0)', '=IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),7.0)', '=IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),"U")', '=IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),"Workshop Upgrade")', '=IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),"Farming")', None, '=IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),"Tourney")', None]
  - ['=IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),"Starting Cash")', '=IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),6.0)', None, '=IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),99.0)', None, None, '=IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),"¢ Level")', '=IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),"$ Level")', '=IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),"¢ Level")', '=IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),"$ Level")']
  - ['=IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),"Workshop Attack Discount")', '=IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),16.0)', None, '=IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),99.0)', None, '=IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),"Damage")', '=IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),5750.0)', '=IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),6000.0)', '=IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),5750.0)', '=IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),6000.0)']
  - ['=IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),"Workshop Defense Discount")', '=IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),19.0)', None, '=IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),99.0)', None, '=IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),"Attack Speed")', '=IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),99.0)', '=IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),99.0)', '=IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),99.0)', '=IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),99.0)']

### Sheet: Themes & Songs
- Dimensions: None rows × None cols
- First non-empty header-like row: 2
- Header values (non-empty): ['Tower Skin', '+0.4%', 'Background Skin', '+0.8%', 'Event Name', 'Reroll', 'Milestone Skin', 'Tier Unlocked', 'Total Bonuses', 'Percent', 'Active', 'Bonus', 'TOTAL', 'BONUS']
- Formula cells: 82 (scanned 1300 cells)
- Top formulas (up to 10):
  - =IF(COUNTIF('Events Timeline'!C:C,H3)>1, COUNTIF('Events Timeline'!C:C,H3)-1, "") (count=1)
  - <openpyxl.worksheet.formula.ArrayFormula object at 0x7ff583391e70> (count=1)
  - =T3/W3 (count=1)
  - =COUNTIF($B$3:B50, True) (count=1)
  - =T3*0.4% (count=1)
  - =COUNTA($B$3:B50) (count=1)
  - =W3*0.4% (count=1)
  - =IF(COUNTIF('Events Timeline'!C:C,H4)>1, COUNTIF('Events Timeline'!C:C,H4)-1, "") (count=1)
  - =T4/W4 (count=1)
  - =COUNTIF($E$3:E50, True) (count=1)
- Preview (first 5 rows × 10 cols):
  - [None, None, None, None, None, None, None, None, None, None]
  - [None, 'Tower Skin', None, '+0.4%', 'Background Skin', None, '+0.8%', 'Event Name', 'Reroll', None]
  - [None, False, 'Star', None, False, 'Interstellar', None, 'Interstellar', '=IF(COUNTIF(\'Events Timeline\'!C:C,H3)>1, COUNTIF(\'Events Timeline\'!C:C,H3)-1, "")', None]
  - [None, False, 'Eye of the Lord', None, False, 'Volcano', None, 'Volcano', '=IF(COUNTIF(\'Events Timeline\'!C:C,H4)>1, COUNTIF(\'Events Timeline\'!C:C,H4)-1, "")', None]
  - [None, True, 'Plasma Ball', None, True, 'Plasma Field', None, 'Plasma Returns', '=IF(COUNTIF(\'Events Timeline\'!C:C,H5)>1, COUNTIF(\'Events Timeline\'!C:C,H5)-1, "")', None]

### Sheet: Events Timeline
- Dimensions: None rows × None cols
- First non-empty header-like row: 2
- Header values (non-empty): ['Event', 'Skin', 'Standard Relics', 'Reroll Relics', 'Premium Relics', 'Start Date']
- Formula cells: 79 (scanned 1162 cells)
- Top formulas (up to 10):
  - =COUNTIF($C4:C$82, C4) (count=1)
  - =COUNTIF($C5:C$82, C5) (count=1)
  - =COUNTIF($C6:C$82, C6) (count=1)
  - =COUNTIF($C7:C$82, C7) (count=1)
  - =COUNTIF($C8:C$82, C8) (count=1)
  - =COUNTIF($C9:C$82, C9) (count=1)
  - =COUNTIF($C10:C$82, C10) (count=1)
  - =COUNTIF($C11:C$82, C11) (count=1)
  - =COUNTIF($C12:C$82, C12) (count=1)
  - =COUNTIF($C13:C$82, C13) (count=1)
- Preview (first 5 rows × 10 cols):
  - [None, None, None, None, None, None, None, None, None, None]
  - [None, 'Event', None, 'Skin', None, 'Standard Relics', None, 'Reroll Relics', None, 'Premium Relics']
  - [None, '#', 'Name', 'Tower', 'Background', '350 Medals', '700 Medals', '200 Medals', '500 Medals', '550 Medals']
  - [None, '=COUNTIF($C4:C$82, C4)', 'Aurora', 'North Spirit', 'Aurora', "Sky's Curtain", 'Northern Mountains', 'Aurora Vortex', 'Contained Ions', 'Solar Flare']
  - [None, '=COUNTIF($C5:C$82, C5)', 'Amusement Park', 'Balloon', 'Amusement Park', 'Hapiness Balloons', 'Amazing Prizes', '-', '-', 'Delicious Food']

### Sheet: EXPORT
- Dimensions: None rows × None cols
- First non-empty header-like row: 2
- Header values (non-empty): ['Active', 'Bonus', 'TOTAL', 'BONUS']
- Formula cells: 32 (scanned 88 cells)
- Top formulas (up to 10):
  - ='Themes & Songs'!T10 (count=1)
  - ='Themes & Songs'!U10 (count=1)
  - ='Themes & Songs'!W10 (count=1)
  - ='Themes & Songs'!X10 (count=1)
  - ='Themes & Songs'!T3 (count=1)
  - ='Themes & Songs'!U3 (count=1)
  - ='Themes & Songs'!W3 (count=1)
  - ='Themes & Songs'!X3 (count=1)
  - ='Themes & Songs'!T4 (count=1)
  - ='Themes & Songs'!U4 (count=1)
- Preview (first 5 rows × 10 cols):
  - ['T&Sv2', None, None, None, None, None, None, None, None, None]
  - [None, None, 'Active', 'Bonus', None, 'TOTAL', 'BONUS', None, None, None]
  - [None, 'Total', "='Themes & Songs'!T10", "='Themes & Songs'!U10", None, "='Themes & Songs'!W10", "='Themes & Songs'!X10", None, None, None]
  - [None, 'Event Tower', "='Themes & Songs'!T3", "='Themes & Songs'!U3", None, "='Themes & Songs'!W3", "='Themes & Songs'!X3", None, None, None]
  - [None, 'Event Background', "='Themes & Songs'!T4", "='Themes & Songs'!U4", None, "='Themes & Songs'!W4", "='Themes & Songs'!X4", None, None, None]
- EXPORT columns (7): ['T&Sv2', 'Unnamed: 1', 'Unnamed: 2', 'Unnamed: 3', 'Unnamed: 4', 'Unnamed: 5', 'Unnamed: 6']
- EXPORT row count: 9

### Sheet: Giveaways
- Dimensions: None rows × None cols
- First non-empty header-like row: 1
- Header values (non-empty): ['=IFERROR(__xludf.DUMMYFUNCTION("ARRAYFORMULA(IMPORTRANGE(""1eCPPuQOE3Pyh8HhnApEMK3RFIutkUjWd61ppVImwWk8"", ""Giveaways_Data!A1:F15"") & """" & TEXT(NOW(),""""))"),"")', '=IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),"")', '=IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),"")', '=IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),"")', '=IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),"")', '=IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),"")']
- Formula cells: 114 (scanned 240 cells)
- Top formulas (up to 10):
  - =IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),"") (count=68)
  - =IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),"#REF!") (count=3)
  - =IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),"Draw on:") (count=3)
  - =IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),"Reward:") (count=3)
  - =IFERROR(__xludf.DUMMYFUNCTION("ARRAYFORMULA(IMPORTRANGE(""1eCPPuQOE3Pyh8HhnApEMK3RFIutkUjWd61ppVImwWk8"", ""Giveaways_Data!A1:F15"") & """" & TEXT(NOW(),""""))"),"") (count=1)
  - =L2 (count=1)
  - =N2 (count=1)
  - =O2 (count=1)
  - =IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),"Event Pack Giveaway") (count=1)
  - =IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),"2 Feb") (count=1)
- Preview (first 5 rows × 10 cols):
  - [None, None, None, None, None, None, None, None, None, '=IFERROR(__xludf.DUMMYFUNCTION("ARRAYFORMULA(IMPORTRANGE(""1eCPPuQOE3Pyh8HhnApEMK3RFIutkUjWd61ppVImwWk8"", ""Giveaways_Data!A1:F15"") & """" & TEXT(NOW(),""""))"),"")']
  - [None, None, '=L2', None, '=N2', '=O2', None, 'Those giveaways are funded by everyone who use my creator code SHEETLORD when buying stuff from the shops.\n\n\nThe more you use my code, the bigger the number of winners will be.\n\n\nI will try to hold giveways before every event, and before every new month. So pay attention to those dates to check if there is any running.\n\n\nPlease remind that the creator code is only set for a duration of 30 days, and after those 30 days the code will disappear - you will have to input it again (both webstore and in game)', None, '=IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),"")']
  - [None, None, '=L3', '=M3', '=IF(N3<>"", HYPERLINK(N3, "Click to participate!"), "")', None, None, None, None, '=IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),"")']
  - [None, None, '=L4', None, None, None, None, None, None, '=IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),"")']
  - [None, '=K5', None, None, None, None, None, None, None, '=IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),"")']

## Copy of UWs v2.1.2.xlsx
- Size: 807233 bytes
- Sheets: Home Page, _IDS, IDS, Master Sheet, UW Cost Calculator v3, GT+  GT dur, GT+  GT Dur Graph, CF+, All UWs, EXPORT, DVT_UWs, DVT_Guardians, WIP

### Sheet: Home Page
- Dimensions: None rows × None cols
- First non-empty header-like row: 4
- Header values (non-empty): ['=HYPERLINK("https://docs.google.com/spreadsheets/d/1T9_3YekZ2jbcebtu0MbuKU5IhI8zUFAR4UvlLklEajw/copy", "UW Initial Link")', 'Sheet Tab', 'Main Contributor', 'Helpers']
- Formula cells: 5 (scanned 275 cells)
- Top formulas (up to 10):
  - =HYPERLINK("https://docs.google.com/spreadsheets/d/1T9_3YekZ2jbcebtu0MbuKU5IhI8zUFAR4UvlLklEajw/copy", "UW Initial Link") (count=1)
  - =IFERROR(__xludf.DUMMYFUNCTION("IMPORTRANGE(""1T9_3YekZ2jbcebtu0MbuKU5IhI8zUFAR4UvlLklEajw"", ""'Home Page'!B12:C13"")"),"v2.1.2") (count=1)
  - =IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),"Feat: GT+ /GT Assist Substat") (count=1)
  - =IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),"v2.1.1") (count=1)
  - =IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),"Fix GT+ /GT dur submod ref") (count=1)
- Preview (first 5 rows × 10 cols):
  - [None, None, None, None, None, None, None, None, None, None]
  - [None, 'Ultimate Weapon', None, None, None, None, None, None, None, None]
  - [None, None, None, None, None, None, None, None, None, None]
  - [None, '=HYPERLINK("https://docs.google.com/spreadsheets/d/1T9_3YekZ2jbcebtu0MbuKU5IhI8zUFAR4UvlLklEajw/copy", "UW Initial Link")', None, None, None, None, 'Sheet Tab', 'Main Contributor', 'Helpers', None]
  - [None, None, None, None, None, None, None, None, None, None]

### Sheet: _IDS
- Dimensions: None rows × None cols
- First non-empty header-like row: 1
- Header values (non-empty): ['=IFERROR(__xludf.DUMMYFUNCTION("IMPORTRANGE(IF(IDS!E6=""✅"", IDS!D6, ""1osjoqKmMwtOWs7Up3e21-3ofN1RHOjsgKV6y3dc6rgE""), ""_IDS!A1:BY212"")"),"Labs")', '=IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),"https://docs.google.com/spreadsheets/d/1yLi6Ni4nZr0Wfct7MmbyNRRi5v6fR62t0kdI-g8NeNo/edit")', '=IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),"✅")', '=IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),"v2.3.2")', '=IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),"WS")', '=IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),"https://docs.google.com/spreadsheets/d/1462mmIeTEmChEYwwpDWacv611QCRW9n-Dvz8oyOQ798/edit")', '=IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),"✅")', '=IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),"v2.2.8")', '=IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),"WS+")', '=IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),"UWs")', '=IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),"https://docs.google.com/spreadsheets/d/1aLEWX2qblJJt96I6QduS_Fp2DjMO6rNToPrUBWGI5BU/edit")', '=IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),"✅")', '=IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),"v2.1.2")', '=IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),"Cards")', '=IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),"https://docs.google.com/spreadsheets/d/1HMQwNLTvcw7aXmjjL7cXmZSdjAF_62ehWpwDIdjqEGs/edit")', '=IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),"✅")', '=IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),"Cards Presets")', '=IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),"v2.2.3")', '=IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),"Relics")', '=IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),"https://docs.google.com/spreadsheets/d/1jtZ_RhMszIY0NzPm-kNhYg_w5D8WDm9tXSJatvVpWDU/edit")', '=IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),"✅")', '=IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),"Vault")', '=IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),"")', '=IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),"Bots")', '=IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),"https://docs.google.com/spreadsheets/d/1gopHNYu4SgI0UbRvscCV4_C1gct7FXr5GBBcjCzCxC0/edit")', '=IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),"✅")', '=IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),"v2.2")', '=IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),"Themes & Songs")', '=IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),"https://docs.google.com/spreadsheets/d/1umYUbdc7TGYJhqFv662Yol9PGzfECdpLYxl4ElV6UwQ/edit")', '=IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),"✅")', '=IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),"Modules")', '=IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),"https://docs.google.com/spreadsheets/d/1mz0hSpsng0Kzlz8xk0VEyRgaE62Gzj5kNLu3Vp-4gGE/edit")', '=IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),"✅")', '=IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),"v5.12")', '=IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),"Guardians")', '=IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),"https://docs.google.com/spreadsheets/d/19vecjglXSr9t51C6vJy-lMGk1xH4h52ytBr-uyKxLcM/edit")', '=IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),"✅")', '=IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),"v2.2.5")']
- Formula cells: 2481 (scanned 20000 cells - truncated)
- Top formulas (up to 10):
  - =IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),"") (count=186)
  - =IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),0.0) (count=171)
  - =IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),99.0) (count=59)
  - =IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),FALSE) (count=54)
  - =IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),20.0) (count=50)
  - =IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),30.0) (count=49)
  - =IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),7.0) (count=46)
  - =IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),1.0) (count=45)
  - =IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),TRUE) (count=36)
  - =IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),9.0) (count=33)
- Preview (first 5 rows × 10 cols):
  - ['=IFERROR(__xludf.DUMMYFUNCTION("IMPORTRANGE(IF(IDS!E6=""✅"", IDS!D6, ""1osjoqKmMwtOWs7Up3e21-3ofN1RHOjsgKV6y3dc6rgE""), ""_IDS!A1:BY212"")"),"Labs")', '=IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),"https://docs.google.com/spreadsheets/d/1yLi6Ni4nZr0Wfct7MmbyNRRi5v6fR62t0kdI-g8NeNo/edit")', '=IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),"✅")', '=IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),"v2.3.2")', '=IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),"WS")', '=IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),"https://docs.google.com/spreadsheets/d/1462mmIeTEmChEYwwpDWacv611QCRW9n-Dvz8oyOQ798/edit")', '=IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),"✅")', '=IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),"v2.2.8")', None, None]
  - ['=IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),"Game Speed")', '=IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),7.0)', '=IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),7.0)', '=IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),7.0)', '=IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),"U")', '=IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),"Workshop Upgrade")', '=IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),"Farming")', None, '=IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),"Tourney")', None]
  - ['=IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),"Starting Cash")', '=IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),6.0)', None, '=IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),99.0)', None, None, '=IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),"¢ Level")', '=IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),"$ Level")', '=IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),"¢ Level")', '=IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),"$ Level")']
  - ['=IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),"Workshop Attack Discount")', '=IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),16.0)', None, '=IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),99.0)', None, '=IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),"Damage")', '=IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),5750.0)', '=IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),6000.0)', '=IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),5750.0)', '=IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),6000.0)']
  - ['=IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),"Workshop Defense Discount")', '=IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),19.0)', None, '=IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),99.0)', None, '=IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),"Attack Speed")', '=IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),99.0)', '=IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),99.0)', '=IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),99.0)', '=IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),99.0)']

### Sheet: IDS
- Dimensions: None rows × None cols
- First non-empty header-like row: 6
- Header values (non-empty): ["IDS Master's ID       ➡️", '18XbHJtHzu8tjqnP_9JcsZFA6jIwjOKRYmzBzOYBMv2I', '=IFERROR(__xludf.DUMMYFUNCTION("IFERROR(C6.url, IFS(LEFT(C6,8)=""https://"", C6, LEN(C6)=44, ""https://docs.google.com/spreadsheets/d/"" & C6 & ""/edit"", TRUE, C6))"),"https://docs.google.com/spreadsheets/d/18XbHJtHzu8tjqnP_9JcsZFA6jIwjOKRYmzBzOYBMv2I/edit")', '=IFERROR(__xludf.DUMMYFUNCTION("IF(D6<>"""", IF(IMPORTRANGE(D6,""EXPORT!A1"") = F6, ""✅"", ""Wrong ID or Version""), """")"),"✅")', 'v2']
- Formula cells: 4 (scanned 268 cells)
- Top formulas (up to 10):
  - =IFERROR(__xludf.DUMMYFUNCTION("IFERROR(C6.url, IFS(LEFT(C6,8)=""https://"", C6, LEN(C6)=44, ""https://docs.google.com/spreadsheets/d/"" & C6 & ""/edit"", TRUE, C6))"),"https://docs.google.com/spreadsheets/d/18XbHJtHzu8tjqnP_9JcsZFA6jIwjOKRYmzBzOYBMv2I/edit") (count=1)
  - =IFERROR(__xludf.DUMMYFUNCTION("IF(D6<>"""", IF(IMPORTRANGE(D6,""EXPORT!A1"") = F6, ""✅"", ""Wrong ID or Version""), """")"),"✅") (count=1)
  - =HYPERLINK("https://docs.google.com/spreadsheets/d/1osjoqKmMwtOWs7Up3e21-3ofN1RHOjsgKV6y3dc6rgE/copy", "1️⃣ Copy Me") (count=1)
  - =IFS(
  ISERROR(E6), "3️⃣ Click on #REF! and then AUTHORISE ↗",
  E6="", "2️⃣ Please input your IDS Master's ID here ⤴️",
  E6="✅", HYPERLINK(D6, "Go to my IDS Master Sheet"),
  TRUE, "") (count=1)
- Preview (first 5 rows × 10 cols):
  - [None, None, None, None, None, None, None, None, None, None]
  - [None, 'The IDS System', None, None, None, None, None, None, 'Looking for the Import script ? Just run it as you were doing it before, but from IDS Master.\nIt will let you import every new versions at once!', None]
  - [None, None, None, None, None, None, None, None, None, None]
  - [None, 'This Sheet ID is :', '1aLEWX2qblJJt96I6QduS_Fp2DjMO6rNToPrUBWGI5BU', None, None, None, None, None, None, None]
  - [None, None, None, None, None, None, None, None, None, None]

### Sheet: Master Sheet
- Dimensions: None rows × None cols
- First non-empty header-like row: 1
- Header values (non-empty): ['Ultimate Weapon', 'Attribute', 'Level', '=IF(\'_IDS\'!C1="✅", HYPERLINK(\'_IDS\'!B1, "Go to my Laboratory Sheet"), "Labs")', 'Level', '=IF(\'_IDS\'!BD1="✅", HYPERLINK(\'_IDS\'!BC1, "Go to my Modules Sheet"), "Modules")', 'Substat', 'Rarity', 'Value']
- Formula cells: 99 (scanned 1300 cells)
- Top formulas (up to 10):
  - =IF('_IDS'!C1="✅", HYPERLINK('_IDS'!B1, "Go to my Laboratory Sheet"), "Labs") (count=1)
  - =IF('_IDS'!BD1="✅", HYPERLINK('_IDS'!BC1, "Go to my Modules Sheet"), "Modules") (count=1)
  - <openpyxl.worksheet.formula.ArrayFormula object at 0x7ff5833dc850> (count=1)
  - =IDS_LAB_LEVEL(I2) (count=1)
  - =IDS_MOD_CANNON_SUBSTATS(N5) (count=1)
  - <openpyxl.worksheet.formula.ArrayFormula object at 0x7ff5833ddf00> (count=1)
  - =IDS_LAB_LEVEL(I3) (count=1)
  - =IF(C4,"UW Unlocked", "UW Locked") (count=1)
  - <openpyxl.worksheet.formula.ArrayFormula object at 0x7ff5833dd600> (count=1)
  - =IDS_LAB_LEVEL(I4) (count=1)
- Preview (first 5 rows × 10 cols):
  - [None, 'Ultimate Weapon', None, None, 'Attribute', None, 'Level', None, '=IF(\'_IDS\'!C1="✅", HYPERLINK(\'_IDS\'!B1, "Go to my Laboratory Sheet"), "Labs")', 'Level']
  - ['ULTIMATE WEAPONS', None, 'Chain Lightning', None, 'Damage', <openpyxl.worksheet.formula.ArrayFormula object at 0x7ff583227a30>, '19 | x898 | Cost 302 ⧌ | Next 362 ⧌', '↓ LABS ↓', 'Chrono Field Duration', '=IDS_LAB_LEVEL(I2)']
  - [None, None, None, None, 'Quantity', <openpyxl.worksheet.formula.ArrayFormula object at 0x7ff5832259f0>, '03 | #4 | Cost 150 ⧌ | Next 400 ⧌', None, 'Golden Tower Bonus', '=IDS_LAB_LEVEL(I3)']
  - [None, None, True, '=IF(C4,"UW Unlocked", "UW Locked")', 'Chance', <openpyxl.worksheet.formula.ArrayFormula object at 0x7ff5832259c0>, '08 | 17.0% | Cost 134 ⧌ | Next 152 ⧌', None, 'Golden Tower Duration', '=IDS_LAB_LEVEL(I4)']
  - [None, None, 'UW+', None, 'Smite', <openpyxl.worksheet.formula.ArrayFormula object at 0x7ff583225b40>, 'Lo | Locked', None, 'Assist Module Substats - Core', '=IDS_LAB_LEVEL(I5)']

### Sheet: UW Cost Calculator v3
- Dimensions: None rows × None cols
- First non-empty header-like row: 2
- Header values (non-empty): ['Total Stones Spent', '=SUM(N9:N68)+H4+K4', '# Of UWs Owned', "=COUNTIF('Master Sheet'!C4:C36, TRUE)", '# Of UW+ Owned', '=9-COUNTIF(D12:D69, "Locked")', 'UW Completion']
- Formula cells: 341 (scanned 1173 cells)
- Top formulas (up to 10):
  - =SUM(N9:N68)+H4+K4 (count=1)
  - =COUNTIF('Master Sheet'!C4:C36, TRUE) (count=1)
  - =9-COUNTIF(D12:D69, "Locked") (count=1)
  - =SUM(O9:O68)+H5+K5 (count=1)
  - =D2/SUM('All UWs'!B1:CI2) (count=1)
  - =SUMIF('All UWs'!B5:B14,"<="&H2, 'All UWs'!C5:C14) (count=1)
  - =SUMIF('All UWs'!D5:D14,"<="&K2, 'All UWs'!E5:E14) (count=1)
  - =D3-D4 (count=1)
  - =SUMIF('All UWs'!B5:B14,"<="&H3, 'All UWs'!C5:C14)-H4 (count=1)
  - =SUMIF('All UWs'!D5:D14,"<="&K3, 'All UWs'!E5:E14)-K4 (count=1)
- Preview (first 5 rows × 10 cols):
  - [None, None, None, None, None, None, None, None, None, None]
  - [None, 'Total Stones Spent', None, '=SUM(N9:N68)+H4+K4', None, '# Of UWs Owned', None, "=COUNTIF('Master Sheet'!C4:C36, TRUE)", '# Of UW+ Owned', None]
  - [None, 'Stones Required', None, '=SUM(O9:O68)+H5+K5', None, '# Of UWs Wanted', None, 9.0, '# Of UW+ Wanted', None]
  - [None, 'Stones Owned Currently', None, 0.0, None, 'Stones Spent', None, '=SUMIF(\'All UWs\'!B5:B14,"<="&H2, \'All UWs\'!C5:C14)', 'Stones Spent', None]
  - [None, 'Stones missing', None, '=D3-D4', None, 'Stone Cost', None, '=SUMIF(\'All UWs\'!B5:B14,"<="&H3, \'All UWs\'!C5:C14)-H4', 'Stone Cost', None]

### Sheet: GT+  GT dur
- Dimensions: None rows × None cols
- First non-empty header-like row: 1
- Header values (non-empty): ['GT+10', 'Increase from 0', '=((1+W8)^($R7*$U3))-1^($R7*$U3)', '=((1+X8)^($R7*$U3))-1^($R7*$U3)', '=((1+Y8)^($R7*$U3))-1^($R7*$U3)', '=((1+Z8)^($R7*$U3))-1^($R7*$U3)', '=((1+AA8)^($R7*$U3))-1^($R7*$U3)', '=((1+AB8)^($R7*$U3))-1^($R7*$U3)', '=((1+AC8)^($R7*$U3))-1^($R7*$U3)', '=((1+AD8)^($R7*$U3))-1^($R7*$U3)', '=((1+AE8)^($R7*$U3))-1^($R7*$U3)', '=((1+AF8)^($R7*$U3))-1^($R7*$U3)', '=((1+AG8)^($R7*$U3))-1^($R7*$U3)']
- Formula cells: 687 (scanned 1958 cells)
- Top formulas (up to 10):
  - =MATCH(G6,R10:R1000)-1 (count=2)
  - =((1+W8)^($R7*$U3))-1^($R7*$U3) (count=1)
  - =((1+X8)^($R7*$U3))-1^($R7*$U3) (count=1)
  - =((1+Y8)^($R7*$U3))-1^($R7*$U3) (count=1)
  - =((1+Z8)^($R7*$U3))-1^($R7*$U3) (count=1)
  - =((1+AA8)^($R7*$U3))-1^($R7*$U3) (count=1)
  - =((1+AB8)^($R7*$U3))-1^($R7*$U3) (count=1)
  - =((1+AC8)^($R7*$U3))-1^($R7*$U3) (count=1)
  - =((1+AD8)^($R7*$U3))-1^($R7*$U3) (count=1)
  - =((1+AE8)^($R7*$U3))-1^($R7*$U3) (count=1)
- Preview (first 5 rows × 10 cols):
  - [None, None, None, None, None, None, None, None, None, None]
  - [None, 'Interactive GT+ vs GT duration calculator\n\nCalculates whether upgrading GT duration or GT+ has the best ROI', None, None, None, None, None, None, None, None]
  - [None, None, None, None, None, None, None, None, None, None]
  - [None, None, None, None, None, None, None, None, None, None]
  - [None, 'GT duration lab Level', None, "='Master Sheet'!J4", 'Start of good CPH wave:', None, 3000.0, None, None, None]

### Sheet: GT+  GT Dur Graph
- Dimensions: None rows × None cols
- First non-empty header-like row: 3
- Header values (non-empty): [0.0003, '=B3+0.03%', '=C3+0.03%', '=D3+0.03%', '=E3+0.03%', '=F3+0.03%', '=G3+0.03%', '=H3+0.03%', '=I3+0.03%', '=J3+0.03%', '=K3+0.03%', '=L3+0.03%', '=M3+0.03%', '=N3+0.03%', '=O3+0.03%']
- Formula cells: 1181 (scanned 1205 cells)
- Top formulas (up to 10):
  - =B3+0.03% (count=1)
  - =C3+0.03% (count=1)
  - =D3+0.03% (count=1)
  - =E3+0.03% (count=1)
  - =F3+0.03% (count=1)
  - =G3+0.03% (count=1)
  - =H3+0.03% (count=1)
  - =I3+0.03% (count=1)
  - =J3+0.03% (count=1)
  - =K3+0.03% (count=1)
- Preview (first 5 rows × 10 cols):
  - ['Kills per Second', None, 7.0, None, None, None, None, None, None, None]
  - [None, None, None, None, None, None, None, None, None, None]
  - [None, 0.0003, '=B3+0.03%', '=C3+0.03%', '=D3+0.03%', '=E3+0.03%', '=F3+0.03%', '=G3+0.03%', '=H3+0.03%', '=I3+0.03%']
  - ['GT dur', 'GT+0', 'GT+1', 'GT+2', 'GT+3', 'GT+4', 'GT+5', 'GT+6', 'GT+7', 'GT+8']
  - ['=15', '=POW(1+B$3, $A5*$C$1)', '=POW(1+C$3, $A5*$C$1)', '=POW(1+D$3, $A5*$C$1)', '=POW(1+E$3, $A5*$C$1)', '=POW(1+F$3, $A5*$C$1)', '=POW(1+G$3, $A5*$C$1)', '=POW(1+H$3, $A5*$C$1)', '=POW(1+I$3, $A5*$C$1)', '=POW(1+J$3, $A5*$C$1)']

### Sheet: CF+
- Dimensions: None rows × None cols
- First non-empty header-like row: 13
- Header values (non-empty): ['CF+ Level', 'Rotation Rate', 'Full Orbit Time', 'CF+ Level', 'Hidden CF+ Slow%', 'Old Enemy Speed', 'New Enemy Speed', 'Enemy Speed Rate']
- Formula cells: 84 (scanned 372 cells)
- Top formulas (up to 10):
  - =0.1+B15*0.05 (count=1)
  - =C15*180/PI()/2 (count=1)
  - =ROUNDUP(360/D15,1)&" seconds" (count=1)
  - =MAX(0.5,G15)*0.05 (count=1)
  - =(I15*(1-H15)) (count=1)
  - =ROUND(100*I15/J15-100,1)&"% slower" (count=1)
  - =0.1+B16*0.05 (count=1)
  - =C16*180/PI()/2 (count=1)
  - =ROUNDUP(360/D16,1)&" seconds" (count=1)
  - =MAX(0.5,G16)*0.05 (count=1)
- Preview (first 5 rows × 10 cols):
  - [None, None, None, None, None, None, None, None, None, None]
  - [None, 'CF+ exerts a tangental force on enemies within CF Range, causing them to spiral around the tower as they approach. \n\nThe rotation rate stated in-game for each CF+ level is the theta value (θ), or the distance measured in radians traveled per 2 seconds. \n\nWith low enough enemy speeds, enemies will appear to be perpetually in orbit around the tower, having faster orbital cycles with higher CF+ levels', None, None, None, None, 'In addition to the rotational rate, CF+ provides a hidden benefit of reducing enemy speed by a percentage, for all enemies within CF Range. This rate of enemy speed reduction increases per CF+ level.\n\nUnlike many of exponential growth stats in The Tower, this slow effect does not suffer diminishing returns as CF+ level increases, but instead becomes stronger with each additional level.', None, None, None]
  - [None, None, None, None, None, None, None, None, None, None]
  - [None, None, None, None, None, None, None, None, None, None]
  - [None, None, None, None, None, None, None, None, None, None]

### Sheet: All UWs
- Dimensions: None rows × None cols
- First non-empty header-like row: 1
- Header values (non-empty): ['=Sum(C$5:C14)', '=Sum(H$5:H66)', '=Sum(J$5:J66)', '=Sum(L$5:L66)', '=Sum(Q$5:Q66)', '=Sum(S$5:S66)', '=Sum(U$5:U66)', '=Sum(Z$5:Z66)', '=Sum(AB$5:AB66)', '=Sum(AD$5:AD66)', '=Sum(AI$5:AI66)', '=Sum(AK$5:AK66)', '=Sum(AM$5:AM66)', '=Sum(AR$5:AR66)', '=Sum(AT$5:AT66)', '=Sum(AV$5:AV66)', '=Sum(BA$5:BA66)', '=Sum(BC$5:BC66)', '=Sum(BE$5:BE66)', '=Sum(BJ$5:BJ66)', '=Sum(BL$5:BL66)', '=Sum(BN$5:BN66)', '=Sum(BS$5:BS66)', '=Sum(BU$5:BU66)', '=Sum(BW$5:BW66)', '=Sum(CB$5:CB66)', '=Sum(CD$5:CD66)', '=Sum(CF$5:CF66)']
- Formula cells: 329 (scanned 5742 cells)
- Top formulas (up to 10):
  - =Sum(C$5:C14) (count=1)
  - =Sum(H$5:H66) (count=1)
  - =Sum(J$5:J66) (count=1)
  - =Sum(L$5:L66) (count=1)
  - =Sum(Q$5:Q66) (count=1)
  - =Sum(S$5:S66) (count=1)
  - =Sum(U$5:U66) (count=1)
  - =Sum(Z$5:Z66) (count=1)
  - =Sum(AB$5:AB66) (count=1)
  - =Sum(AD$5:AD66) (count=1)
- Preview (first 5 rows × 10 cols):
  - [None, None, '=Sum(C$5:C14)', None, None, None, None, '=Sum(H$5:H66)', None, '=Sum(J$5:J66)']
  - [None, None, None, None, '=Sum(E$5:E14)', None, None, None, None, None]
  - [None, 'Unlock Costs per UW', None, 'Unlock Costs per UW+', None, None, 'Chain Lightning', None, None, None]
  - [None, 'UW', 'Cost', 'UW+', 'Cost', None, 'Damage', 'Cost', 'Quantity', 'Cost']
  - ['ULTIMATE WEAPONS UNLOCKS', 0.0, 0.0, 0.0, 0.0, 'CHAIN LIGHTNING', 2.0, 0.0, 1.0, 0.0]

### Sheet: EXPORT
- Dimensions: None rows × None cols
- First non-empty header-like row: 4
- Header values (non-empty): ['Ultimate Weapon', 'Attribute', 'Level']
- Formula cells: 91 (scanned 328 cells)
- Top formulas (up to 10):
  - ='UW Cost Calculator v3'!D2 (count=1)
  - ='Master Sheet'!F2 (count=1)
  - ='Master Sheet'!G2 (count=1)
  - ='Master Sheet'!F3 (count=1)
  - ='Master Sheet'!G3 (count=1)
  - ='Master Sheet'!C4 (count=1)
  - ='Master Sheet'!D4 (count=1)
  - ='Master Sheet'!F4 (count=1)
  - ='Master Sheet'!G4 (count=1)
  - ='Master Sheet'!F5 (count=1)
- Preview (first 5 rows × 10 cols):
  - ['Uv2', None, None, None, None, None, None, None, None, None]
  - [None, 'Stones Spent', None, None, "='UW Cost Calculator v3'!D2", None, None, None, None, None]
  - [None, None, None, None, None, None, None, None, None, None]
  - [None, 'Ultimate Weapon', None, None, 'Attribute', None, 'Level', None, None, None]
  - [None, None, 'Chain Lightning', None, 'Damage', "='Master Sheet'!F2", "='Master Sheet'!G2", None, None, None]
- EXPORT columns (7): ['Uv2', 'Unnamed: 1', 'Unnamed: 2', 'Unnamed: 3', 'Unnamed: 4', 'Unnamed: 5', 'Unnamed: 6']
- EXPORT row count: 39

### Sheet: DVT_UWs
- Dimensions: None rows × None cols
- First non-empty header-like row: 1
- Header values (non-empty): ['DVT_UW_UG_CL_DMG', 'DVT_UW_UG_CL_QNT', 'DVT_UW_UG_CL_CH', 'DVT_UW_UG_CL_SM', 'Chain Lightning', 'Chain Lightning +', 'DVT_UW_UG_SM_DMG', 'DVT_UW_UG_SM_QNT', 'DVT_UW_UG_SM_CD', 'DVT_UW_UG_SM_CF', 'Smart Missiles', 'Smart Missiles +', 'DVT_UW_UG_DW_DMG', 'DVT_UW_UG_DW_QNT', 'DVT_UW_UG_DW_CD', 'DVT_UW_UG_DW_KW', 'Death Wave', 'Death Wave +', 'DVT_UW_UG_CF_DU', 'DVT_UW_UG_CF_SP', 'DVT_UW_UG_CF_CD', 'DVT_UW_UG_CF_CL', 'Chrono Field', 'Chrono Field +', 'DVT_UW_UG_ILM_DMG', 'DVT_UW_UG_ILM_QNT', 'DVT_UW_UG_ILM_CD', 'DVT_UW_UG_ILM_CM', 'Inner Land Mines', 'Inner Land Mines +', 'DVT_UW_UG_GT_M', 'DVT_UW_UG_GT_GC', 'DVT_UW_UG_GT_CD', 'DVT_UW_UG_GT_GC', 'Golden Tower', 'Golden Tower +', 'DVT_UW_UG_PS_DMG', 'DVT_UW_UG_PS_DU', 'DVT_UW_UG_PS_CH', 'DVT_UW_UG_PS_DC', 'Poison Swamp', 'Poison Swamp +', 'DVT_UW_UG_BH_SZ', 'DVT_UW_UG_BH_DU', 'DVT_UW_UG_BH_CD', 'DVT_UW_UG_BH_C', 'Black Hole', 'Black Hole +', 'DVT_UW_UG_SL_MU', 'DVT_UW_UG_SL_AN', 'DVT_UW_UG_SL_QNT', 'DVT_UW_UG_SL_LR', 'Spotlight', 'Spotlight +']
- Formula cells: 723 (scanned 20000 cells - truncated)
- Top formulas (up to 10):
  - =TEXT(G3,"00") & " | " & TEXT(H3, "x0") & " | Cost " & I3 & " ⧌ |" & IF(I4="Max", " Maxed", " Next " & I4 & " ⧌") (count=1)
  - =TEXT(G3,"00") & " | #" & TEXT(J3, "0") & " | Cost " & K3 & " ⧌ |" & IF(K4="Max", " Maxed", " Next " & K4 & " ⧌") (count=1)
  - =TEXT(G3,"00") & " | " & TEXT(L3*100, "0.0") & "% | Cost " & M3 & " ⧌ |" & IF(M4="Max", " Maxed", " Next " & M4 & " ⧌") (count=1)
  - <openpyxl.worksheet.formula.ArrayFormula object at 0x7ff5831b6140> (count=1)
  - =TEXT(U3,"00") & " | " & TEXT(V3, "x0") & " | Cost " & W3 & " ⧌ |" & IF(W4="Max", " Maxed", " Next " & W4 & " ⧌") (count=1)
  - =TEXT(U3,"00") & " | #" & TEXT(X3, "0") & " | Cost " & Y3 & " ⧌ |" & IF(Y4="Max", " Maxed", " Next " & Y4 & " ⧌") (count=1)
  - =TEXT(U3,"00") & " | " & TEXT(Z3, "0") & "s | Cost " & AA3 & " ⧌ |" & IF(AA4="Max", " Maxed", " Next " & AA4 & " ⧌") (count=1)
  - <openpyxl.worksheet.formula.ArrayFormula object at 0x7ff5831b7d90> (count=1)
  - =TEXT(AI3,"00") & " | " & TEXT(AJ3, "x0") & " | Cost " & AK3 & " ⧌ |" & IF(AK4="Max", " Maxed", " Next " & AK4 & " ⧌") (count=1)
  - =TEXT(AI3,"00") & " | #" & TEXT(AL3, "0") & " | Cost " & AM3 & " ⧌ |" & IF(AM4="Max", " Maxed", " Next " & AM4 & " ⧌") (count=1)
- Preview (first 5 rows × 10 cols):
  - [None, None, 'DVT_UW_UG_CL_DMG', 'DVT_UW_UG_CL_QNT', 'DVT_UW_UG_CL_CH', 'DVT_UW_UG_CL_SM', None, 'Chain Lightning', None, None]
  - ['ULTIMATE WEAPONS', 'Chain Ligtning', None, None, None, None, None, 'Damage', 'Cost', 'Quantity']
  - [None, None, '=TEXT(G3,"00") & " | " & TEXT(H3, "x0") & " | Cost " & I3 & " ⧌ |" & IF(I4="Max", " Maxed", " Next " & I4 & " ⧌")', '=TEXT(G3,"00") & " | #" & TEXT(J3, "0") & " | Cost " & K3 & " ⧌ |" & IF(K4="Max", " Maxed", " Next " & K4 & " ⧌")', '=TEXT(G3,"00") & " | " & TEXT(L3*100, "0.0") & "% | Cost " & M3 & " ⧌ |" & IF(M4="Max", " Maxed", " Next " & M4 & " ⧌")', 'Lo | Locked', 0.0, <openpyxl.worksheet.formula.ArrayFormula object at 0x7ff58300e6e0>, 0.0, 1.0]
  - [None, None, '=TEXT(G4,"00") & " | " & TEXT(H4, "x0") & " | Cost " & I4 & " ⧌ |" & IF(I5="Max", " Maxed", " Next " & I5 & " ⧌")', '=TEXT(G4,"00") & " | #" & TEXT(J4, "0") & " | Cost " & K4 & " ⧌ |" & IF(K5="Max", " Maxed", " Next " & K5 & " ⧌")', '=TEXT(G4,"00") & " | " & TEXT(L4*100, "0.0") & "% | Cost " & M4 & " ⧌ |" & IF(M5="Max", " Maxed", " Next " & M5 & " ⧌")', '=TEXT(G3,"00") & " | " & TEXT(N4*100, "0.00") & "% | Cost " & O4 & " ⧌ |" & IF(O5="Max", " Maxed", " Next " & O5 & " ⧌")', 1.0, 3.0, 5.0, 2.0]
  - [None, None, '=TEXT(G5,"00") & " | " & TEXT(H5, "x0") & " | Cost " & I5 & " ⧌ |" & IF(I6="Max", " Maxed", " Next " & I6 & " ⧌")', '=TEXT(G5,"00") & " | #" & TEXT(J5, "0") & " | Cost " & K5 & " ⧌ |" & IF(K6="Max", " Maxed", " Next " & K6 & " ⧌")', '=TEXT(G5,"00") & " | " & TEXT(L5*100, "0.0") & "% | Cost " & M5 & " ⧌ |" & IF(M6="Max", " Maxed", " Next " & M6 & " ⧌")', '=TEXT(G4,"00") & " | " & TEXT(N5*100, "0.00") & "% | Cost " & O5 & " ⧌ |" & IF(O6="Max", " Maxed", " Next " & O6 & " ⧌")', 2.0, 5.0, 11.0, 3.0]

### Sheet: DVT_Guardians
- Dimensions: None rows × None cols
- First non-empty header-like row: 1
- Header values (non-empty): ['=IFERROR(__xludf.DUMMYFUNCTION("IMPORTRANGE(""1Q8dhx05NIzgk1JNbZkdL-Y6cX07U09AiFkct4p1tZg4"", ""DVT_Guardians!A1:BD"")"),"")', '=IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),"DVT_GAR_UG_AT_PER")', '=IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),"DVT_GAR_UG_AT_COO")', '=IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),"DVT_GAR_UG_AT_TAR")', '=IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),"Attack")', '=IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),"DVT_GAR_UG_AL_REC")', '=IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),"DVT_GAR_UG_AL_MAX")', '=IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),"DVT_GAR_UG_AL_COO")', '=IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),"Ally")', '=IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),"DVT_GAR_UG_BO_MUL")', '=IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),"DVT_GAR_UG_BO_COO")', '=IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),"DVT_GAR_UG_BO_TAR")', '=IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),"Bounty")', '=IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),"DVT_GAR_UG_FE_COO")', '=IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),"DVT_GAR_UG_FE_FIN")', '=IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),"DVT_GAR_UG_FE_DOU")', '=IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),"Fetch")', '=IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),"DVT_GAR_UG_SU_COO")', '=IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),"DVT_GAR_UG_SU_DUR")', '=IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),"DVT_GAR_UG_SU_CAS")', '=IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),"Summon")']
- Formula cells: 2669 (scanned 20000 cells - truncated)
- Top formulas (up to 10):
  - =IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),0.0) (count=35)
  - =IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),10.0) (count=17)
  - =IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),75.0) (count=17)
  - =IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),30.0) (count=17)
  - =IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),35.0) (count=17)
  - =IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),60.0) (count=17)
  - =IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),70.0) (count=17)
  - =IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),25.0) (count=16)
  - =IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),50.0) (count=16)
  - =IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),45.0) (count=16)
- Preview (first 5 rows × 10 cols):
  - ['=IFERROR(__xludf.DUMMYFUNCTION("IMPORTRANGE(""1Q8dhx05NIzgk1JNbZkdL-Y6cX07U09AiFkct4p1tZg4"", ""DVT_Guardians!A1:BD"")"),"")', None, '=IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),"DVT_GAR_UG_AT_PER")', '=IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),"DVT_GAR_UG_AT_COO")', '=IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),"DVT_GAR_UG_AT_TAR")', None, '=IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),"Attack")', None, None, None]
  - ['=IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),"GUARDIANS")', '=IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),"ATTACK")', None, None, None, None, '=IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),"Percentage")', '=IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),"Cost")', '=IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),"Cooldown")', '=IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),"Cost")']
  - [None, None, None, None, None, None, '=IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),"Locked")', '=IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),0.0)', '=IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),"Locked")', '=IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),0.0)']
  - [None, None, '=IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),"00 | 1% | Cost 0 ⧈ | Next 25 ⧈")', '=IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),"00 | 120s | Cost 0 ⧈ | Next 1 ⧈")', '=IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),"00 | 1 | Cost 0 ⧈ | Next 100 ⧈")', '=IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),0.0)', '=IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),0.01)', '=IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),0.0)', '=IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),120.0)', '=IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),0.0)']
  - [None, None, '=IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),"01 | 2% | Cost 25 ⧈ | Next 50 ⧈")', '=IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),"01 | 119s | Cost 1 ⧈ | Next 2 ⧈")', '=IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),"01 | 2 | Cost 100 ⧈ | Next 200 ⧈")', '=IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),1.0)', '=IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),0.02)', '=IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),25.0)', '=IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),119.0)', '=IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),1.0)']

### Sheet: WIP
- Dimensions: None rows × None cols
- First non-empty header-like row: 3
- Header values (non-empty): ['Angle', 'SPOTLIGHT PATH', 'UPDATE RUNNING', 'Bonus', 'SIMULATIONS', 'TIME USAGE vs GAIN', 'MATRIX']
- Formula cells: 1138 (scanned 2625 cells)
- Top formulas (up to 10):
  - =IFERROR(__xludf.DUMMYFUNCTION("IF(F6<>"""", SPARKLINE(J5:J35), ""Completed ! 🎉"")"),"") (count=1)
  - =V5 (count=1)
  - =VALUE(LEFT('Master Sheet'!G35, 2)) (count=1)
  - =VALUE(LEFT('Master Sheet'!G36, 2)) (count=1)
  - =VALUE(LEFT('Master Sheet'!G34, 2)) (count=1)
  - =DVT_UW_STAT("Spotlight", "Quantity", R5+5) (count=1)
  - =LET(
  Angle, DVT_UW_STAT("Spotlight", "Angle", Q5),
  Quantity, DVT_UW_STAT("Spotlight", "Quantity", R5),
  Multiplier, DVT_UW_STAT("Spotlight", "Multiplier", S5),

Angle * Quantity / 360 * Multiplier) (count=1)
  - =IF(DVT_UW_COST("Spotlight", "Angle", Q5+2)="", "", LET(
  Angle, DVT_UW_STAT("Spotlight", "Angle", Q5+1),
  Quantity, DVT_UW_STAT("Spotlight", "Quantity", R5),
  Multiplier, DVT_UW_STAT("Spotlight", "Multiplier", S5),

Angle * Quantity / 360 * Multiplier)) (count=1)
  - =IF(DVT_UW_COST("Spotlight", "Quantity", R5+2)="", "", LET(
  Angle, DVT_UW_STAT("Spotlight", "Angle", Q5),
  Quantity, DVT_UW_STAT("Spotlight", "Quantity", R5+1),
  Multiplier, DVT_UW_STAT("Spotlight", "Multiplier", S5),

Angle * Quantity / 360 * Multiplier)) (count=1)
  - =IF(DVT_UW_COST("Spotlight", "Multiplier", S5+2)="", "", LET(
  Angle, DVT_UW_STAT("Spotlight", "Angle", Q5),
  Quantity, DVT_UW_STAT("Spotlight", "Quantity", R5),
  Multiplier, DVT_UW_STAT("Spotlight", "Multiplier", S5+1),

Angle * Quantity / 360 * Multiplier)) (count=1)
- Preview (first 5 rows × 10 cols):
  - [None, None, None, None, None, None, None, None, None, None]
  - [None, None, None, None, None, '=IFERROR(__xludf.DUMMYFUNCTION("IF(F6<>"""", SPARKLINE(J5:J35), ""Completed ! 🎉"")"),"")', None, None, None, None]
  - [None, None, 'Angle', None, 'SPOTLIGHT PATH', None, None, None, None, None]
  - [None, None, 'Quantity', None, None, 'Upgrade', 'Level', 'Cost', 'ROI / Stone', 'Final Bonus']
  - [None, None, 'Multiplier', None, None, None, None, None, None, None]

## Copy of Workshop v2.2.8.xlsx
- Size: 1250735 bytes
- Sheets: Home Page, IDS, _IDS, Master Sheet, Desired Ratios, Goldbox Calculator, ELS+ ROI Calculator, Coins+ vs ELS+, DVT_Workshop, EXPORT, Workshop Enhancement Prices

### Sheet: Home Page
- Dimensions: None rows × None cols
- First non-empty header-like row: 4
- Header values (non-empty): ['=HYPERLINK("https://docs.google.com/spreadsheets/d/1GRVlWERQmvfHgsWytiY6gJn8-7oDDnGbg1Bsb5x4TS8/copy", "Workshop Initial Link")', 'Sheet Tab', 'Main Contributor', 'Helpers']
- Formula cells: 5 (scanned 341 cells)
- Top formulas (up to 10):
  - =HYPERLINK("https://docs.google.com/spreadsheets/d/1GRVlWERQmvfHgsWytiY6gJn8-7oDDnGbg1Bsb5x4TS8/copy", "Workshop Initial Link") (count=1)
  - =IFERROR(__xludf.DUMMYFUNCTION("IMPORTRANGE(""1GRVlWERQmvfHgsWytiY6gJn8-7oDDnGbg1Bsb5x4TS8"", ""'Home Page'!B12:C13"")"),"v2.2.8") (count=1)
  - =IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),"Feat: presets for Desired Ratios") (count=1)
  - =IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),"v2.2.7") (count=1)
  - =IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),"Fix: Coins+ vs ELS+ used wrong EALS/ EHLS stats") (count=1)
- Preview (first 5 rows × 10 cols):
  - [None, None, None, None, None, None, None, None, None, None]
  - [None, 'Workshop', None, None, None, None, None, None, None, None]
  - [None, None, None, None, None, None, None, None, None, None]
  - [None, '=HYPERLINK("https://docs.google.com/spreadsheets/d/1GRVlWERQmvfHgsWytiY6gJn8-7oDDnGbg1Bsb5x4TS8/copy", "Workshop Initial Link")', None, None, None, None, 'Sheet Tab', 'Main Contributor', 'Helpers', None]
  - [None, None, None, None, None, None, None, None, None, None]

### Sheet: IDS
- Dimensions: None rows × None cols
- First non-empty header-like row: 6
- Header values (non-empty): ["IDS Master's ID       ➡️", '18XbHJtHzu8tjqnP_9JcsZFA6jIwjOKRYmzBzOYBMv2I', '=IFERROR(__xludf.DUMMYFUNCTION("IFERROR(C6.url, IFS(LEFT(C6,8)=""https://"", C6, LEN(C6)=44, ""https://docs.google.com/spreadsheets/d/"" & C6 & ""/edit"", TRUE, C6))"),"https://docs.google.com/spreadsheets/d/18XbHJtHzu8tjqnP_9JcsZFA6jIwjOKRYmzBzOYBMv2I/edit")', '=IFERROR(__xludf.DUMMYFUNCTION("IF(D6<>"""", IF(IMPORTRANGE(D6,""EXPORT!A1"") = F6, ""✅"", ""Wrong ID or Version""), """")"),"✅")', 'v2']
- Formula cells: 4 (scanned 268 cells)
- Top formulas (up to 10):
  - =IFERROR(__xludf.DUMMYFUNCTION("IFERROR(C6.url, IFS(LEFT(C6,8)=""https://"", C6, LEN(C6)=44, ""https://docs.google.com/spreadsheets/d/"" & C6 & ""/edit"", TRUE, C6))"),"https://docs.google.com/spreadsheets/d/18XbHJtHzu8tjqnP_9JcsZFA6jIwjOKRYmzBzOYBMv2I/edit") (count=1)
  - =IFERROR(__xludf.DUMMYFUNCTION("IF(D6<>"""", IF(IMPORTRANGE(D6,""EXPORT!A1"") = F6, ""✅"", ""Wrong ID or Version""), """")"),"✅") (count=1)
  - =HYPERLINK("https://docs.google.com/spreadsheets/d/1osjoqKmMwtOWs7Up3e21-3ofN1RHOjsgKV6y3dc6rgE/copy", "1️⃣ Copy Me") (count=1)
  - =IFS(
  ISERROR(E6), "3️⃣ Click on #REF! and then AUTHORISE ↗",
  E6="", "2️⃣ Please input your IDS Master's ID here ⤴️",
  E6="✅", HYPERLINK(D6, "Go to my IDS Master Sheet"),
  TRUE, "") (count=1)
- Preview (first 5 rows × 10 cols):
  - [None, None, None, None, None, None, None, None, None, None]
  - [None, 'The IDS System', None, None, None, None, None, None, 'Looking for the Import script ? Just run it as you were doing it before, but from IDS Master.\nIt will let you import every new versions at once!', None]
  - [None, None, None, None, None, None, None, None, None, None]
  - [None, 'This Sheet ID is :', '1462mmIeTEmChEYwwpDWacv611QCRW9n-Dvz8oyOQ798', None, None, None, None, None, None, None]
  - [None, None, None, None, None, None, None, None, None, None]

### Sheet: _IDS
- Dimensions: None rows × None cols
- First non-empty header-like row: 1
- Header values (non-empty): ['=IFERROR(__xludf.DUMMYFUNCTION("IMPORTRANGE(IF(IDS!E6=""✅"", IDS!D6, ""1osjoqKmMwtOWs7Up3e21-3ofN1RHOjsgKV6y3dc6rgE""), ""_IDS!A1:BY212"")"),"Labs")', '=IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),"https://docs.google.com/spreadsheets/d/1yLi6Ni4nZr0Wfct7MmbyNRRi5v6fR62t0kdI-g8NeNo/edit")', '=IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),"✅")', '=IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),"v2.3.2")', '=IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),"WS")', '=IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),"https://docs.google.com/spreadsheets/d/1462mmIeTEmChEYwwpDWacv611QCRW9n-Dvz8oyOQ798/edit")', '=IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),"✅")', '=IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),"v2.2.8")', '=IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),"WS+")', '=IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),"UWs")', '=IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),"https://docs.google.com/spreadsheets/d/1aLEWX2qblJJt96I6QduS_Fp2DjMO6rNToPrUBWGI5BU/edit")', '=IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),"✅")', '=IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),"v2.1.2")', '=IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),"Cards")', '=IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),"https://docs.google.com/spreadsheets/d/1HMQwNLTvcw7aXmjjL7cXmZSdjAF_62ehWpwDIdjqEGs/edit")', '=IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),"✅")', '=IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),"Cards Presets")', '=IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),"v2.2.3")', '=IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),"Relics")', '=IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),"https://docs.google.com/spreadsheets/d/1jtZ_RhMszIY0NzPm-kNhYg_w5D8WDm9tXSJatvVpWDU/edit")', '=IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),"✅")', '=IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),"Vault")', '=IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),"")', '=IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),"Bots")', '=IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),"https://docs.google.com/spreadsheets/d/1gopHNYu4SgI0UbRvscCV4_C1gct7FXr5GBBcjCzCxC0/edit")', '=IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),"✅")', '=IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),"v2.2")', '=IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),"Themes & Songs")', '=IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),"https://docs.google.com/spreadsheets/d/1umYUbdc7TGYJhqFv662Yol9PGzfECdpLYxl4ElV6UwQ/edit")', '=IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),"✅")', '=IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),"Modules")', '=IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),"https://docs.google.com/spreadsheets/d/1mz0hSpsng0Kzlz8xk0VEyRgaE62Gzj5kNLu3Vp-4gGE/edit")', '=IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),"✅")', '=IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),"v5.12")', '=IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),"Guardians")', '=IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),"https://docs.google.com/spreadsheets/d/19vecjglXSr9t51C6vJy-lMGk1xH4h52ytBr-uyKxLcM/edit")', '=IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),"✅")', '=IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),"v2.2.5")']
- Formula cells: 2481 (scanned 20000 cells - truncated)
- Top formulas (up to 10):
  - =IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),"") (count=186)
  - =IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),0.0) (count=171)
  - =IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),99.0) (count=59)
  - =IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),FALSE) (count=54)
  - =IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),20.0) (count=50)
  - =IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),30.0) (count=49)
  - =IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),7.0) (count=46)
  - =IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),1.0) (count=45)
  - =IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),TRUE) (count=36)
  - =IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),9.0) (count=33)
- Preview (first 5 rows × 10 cols):
  - ['=IFERROR(__xludf.DUMMYFUNCTION("IMPORTRANGE(IF(IDS!E6=""✅"", IDS!D6, ""1osjoqKmMwtOWs7Up3e21-3ofN1RHOjsgKV6y3dc6rgE""), ""_IDS!A1:BY212"")"),"Labs")', '=IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),"https://docs.google.com/spreadsheets/d/1yLi6Ni4nZr0Wfct7MmbyNRRi5v6fR62t0kdI-g8NeNo/edit")', '=IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),"✅")', '=IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),"v2.3.2")', '=IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),"WS")', '=IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),"https://docs.google.com/spreadsheets/d/1462mmIeTEmChEYwwpDWacv611QCRW9n-Dvz8oyOQ798/edit")', '=IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),"✅")', '=IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),"v2.2.8")', None, None]
  - ['=IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),"Game Speed")', '=IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),7.0)', '=IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),7.0)', '=IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),7.0)', '=IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),"U")', '=IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),"Workshop Upgrade")', '=IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),"Farming")', None, '=IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),"Tourney")', None]
  - ['=IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),"Starting Cash")', '=IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),6.0)', None, '=IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),99.0)', None, None, '=IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),"¢ Level")', '=IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),"$ Level")', '=IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),"¢ Level")', '=IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),"$ Level")']
  - ['=IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),"Workshop Attack Discount")', '=IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),16.0)', None, '=IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),99.0)', None, '=IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),"Damage")', '=IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),5750.0)', '=IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),6000.0)', '=IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),5750.0)', '=IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),6000.0)']
  - ['=IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),"Workshop Defense Discount")', '=IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),19.0)', None, '=IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),99.0)', None, '=IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),"Attack Speed")', '=IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),99.0)', '=IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),99.0)', '=IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),99.0)', '=IFERROR(__xludf.DUMMYFUNCTION("""COMPUTED_VALUE"""),99.0)']

### Sheet: Master Sheet
- Dimensions: None rows × None cols
- First non-empty header-like row: 1
- Header values (non-empty): ['Unlock', '=IF(\'_IDS\'!G1="✅", HYPERLINK(\'_IDS\'!F1, "Go to my Workshop Sheet"), "Workshop Upgrade")', 'Farming', 'Tourney', 'Preset 3', 'Preset 4', 'Preset 5', 'Max', '=IF(\'_IDS\'!F1="✅", HYPERLINK(\'_IDS\'!E1, "Go to my Workshop Sheet"), "Workshop Enhancement")', 'Farming', 'Tourney', 'Preset 3', 'Preset 4', 'Preset 5', 'Max', '=IF(\'_IDS\'!C1="✅", HYPERLINK(\'_IDS\'!B1, "Go to my Laboratory Sheet"), "Labs")', 'Level', 'Max', 'Card Preset', '=IF(\'_IDS\'!AT1="✅", HYPERLINK(\'_IDS\'!AS1, "Go to my Modules Sheet"), "Module")', 'Substat', 'Value']
- Formula cells: 269 (scanned 2442 cells)
- Top formulas (up to 10):
  - =IF('_IDS'!G1="✅", HYPERLINK('_IDS'!F1, "Go to my Workshop Sheet"), "Workshop Upgrade") (count=1)
  - =IF('_IDS'!F1="✅", HYPERLINK('_IDS'!E1, "Go to my Workshop Sheet"), "Workshop Enhancement") (count=1)
  - =IF('_IDS'!C1="✅", HYPERLINK('_IDS'!B1, "Go to my Laboratory Sheet"), "Labs") (count=1)
  - =IF('_IDS'!AT1="✅", HYPERLINK('_IDS'!AS1, "Go to my Modules Sheet"), "Module") (count=1)
  - =D3 (count=1)
  - =E3 (count=1)
  - =IF(OR(AA3=1, R3<>0), "Damage +", "Unlock Damage + (Lab)") (count=1)
  - =Sum((R3*0.01)+1) (count=1)
  - =R3 (count=1)
  - =IDS_LAB_LEVEL(Y3) (count=1)
- Preview (first 5 rows × 10 cols):
  - [None, 'Unlock', '=IF(\'_IDS\'!G1="✅", HYPERLINK(\'_IDS\'!F1, "Go to my Workshop Sheet"), "Workshop Upgrade")', 'Farming', None, 'Tourney', None, 'Preset 3', None, 'Preset 4']
  - [None, None, None, '¢ Level', '$ Level', '¢ Level', '$ Level', '¢ Level', '$ Level', '¢ Level']
  - ['↓ WORKSHOP ↓', None, 'Damage', 5750.0, 6000.0, '=D3', '=E3', None, None, None]
  - [None, None, 'Attack Speed', 99.0, 99.0, '=D4', '=E4', None, None, None]
  - [None, None, 'Critical Chance', 79.0, 79.0, '=D5', '=E5', None, None, None]

### Sheet: Desired Ratios
- Dimensions: None rows × None cols
- First non-empty header-like row: 1
- Header values (non-empty): ['v1.6.0', 'Workshop Enhancement', "='Master Sheet'!R1", 'Order', "='Master Sheet'!S1", 'Order', "='Master Sheet'!T1", 'Order', "='Master Sheet'!U1", 'Order', "='Master Sheet'!V1", 'Order', 'Workshop Enhancement', 'Level', 'CostValue', 'CumulatedCost', 'Cost', <openpyxl.worksheet.formula.ArrayFormula object at 0x7ff583191570>, 'Level', 'Desired Fraction', 'Order', <openpyxl.worksheet.formula.ArrayFormula object at 0x7ff583190e50>, 'Rend Armor', 'Critical Factor', 'Damage/Meter', 'Super Crit Mult', 'Attack Speed', 'Health', 'Health Regen', 'Defense Absolute', 'Land Mine Damage', 'Wall Health', 'Orb Size', 'Cash Bonus', 'Coin Bonus', 'Cells / Kill Bonus', 'Free Upgrades', 'Recovery Package', 'Enemy Level Skips', <openpyxl.worksheet.formula.ArrayFormula object at 0x7ff583192830>, 'Rend Armor', 'Critical Factor', 'Damage/Meter', 'Super Crit Mult', 'Attack Speed', 'Health', 'Health Regen', 'Defense Absolute', 'Land Mine Damage', 'Wall Health', 'Orb Size', 'Cash Bonus', 'Coin Bonus', 'Cells / Kill Bonus', 'Free Upgrades', 'Recovery Package', 'Enemy Level Skips', <openpyxl.worksheet.formula.ArrayFormula object at 0x7ff583193910>, 'Rend Armor', 'Critical Factor', 'Damage/Meter', 'Super Crit Mult', 'Attack Speed', 'Health', 'Health Regen', 'Defense Absolute', 'Land Mine Damage', 'Wall Health', 'Orb Size', 'Cash Bonus', 'Coin Bonus', 'Cells / Kill Bonus', 'Free Upgrades', 'Recovery Package', 'Enemy Level Skips', <openpyxl.worksheet.formula.ArrayFormula object at 0x7ff583192ef0>, 'Rend Armor', 'Critical Factor', 'Damage/Meter', 'Super Crit Mult', 'Attack Speed', 'Health', 'Health Regen', 'Defense Absolute', 'Land Mine Damage', 'Wall Health', 'Orb Size', 'Cash Bonus', 'Coin Bonus', 'Cells / Kill Bonus', 'Free Upgrades', 'Recovery Package', 'Enemy Level Skips', <openpyxl.worksheet.formula.ArrayFormula object at 0x7ff583191600>, 'Rend Armor', 'Critical Factor', 'Damage/Meter', 'Super Crit Mult', 'Attack Speed', 'Health', 'Health Regen', 'Defense Absolute', 'Land Mine Damage', 'Wall Health', 'Orb Size', 'Cash Bonus', 'Coin Bonus', 'Cells / Kill Bonus', 'Free Upgrades', 'Recovery Package', 'Enemy Level Skips']
- Formula cells: 7952 (scanned 12648 cells)
- Top formulas (up to 10):
  - ='Master Sheet'!R1 (count=1)
  - ='Master Sheet'!S1 (count=1)
  - ='Master Sheet'!T1 (count=1)
  - ='Master Sheet'!U1 (count=1)
  - ='Master Sheet'!V1 (count=1)
  - <openpyxl.worksheet.formula.ArrayFormula object at 0x7ff5831920e0> (count=1)
  - <openpyxl.worksheet.formula.ArrayFormula object at 0x7ff583190be0> (count=1)
  - <openpyxl.worksheet.formula.ArrayFormula object at 0x7ff5831909a0> (count=1)
  - <openpyxl.worksheet.formula.ArrayFormula object at 0x7ff583190bb0> (count=1)
  - <openpyxl.worksheet.formula.ArrayFormula object at 0x7ff583191c60> (count=1)
- Preview (first 5 rows × 10 cols):
  - ['v1.6.0', 'Workshop Enhancement', "='Master Sheet'!R1", 'Order', "='Master Sheet'!S1", 'Order', "='Master Sheet'!T1", 'Order', "='Master Sheet'!U1", 'Order']
  - [None, <openpyxl.worksheet.formula.ArrayFormula object at 0x7ff5833df490>, '1/8', None, '1/2', None, None, None, None, None]
  - [None, 'Rend Armor', None, None, None, None, None, None, None, None]
  - [None, 'Critical Factor', '1/8', None, '1/1', None, None, None, None, None]
  - [None, 'Damage/Meter', None, None, None, None, None, None, None, None]

### Sheet: Goldbox Calculator
- Dimensions: None rows × None cols
- First non-empty header-like row: 4
- Header values (non-empty): ['Free Attack Upgrade', "=LET(\n  Base,LET(\n    WS,0%+'Master Sheet'!D42*0.5%,\n    Cards, IF(ISNUMBER(L5), 3% + L5 * 1%, 0),\n    Substat, $L9,\n    WS + Cards + Substat),\n  PerkFreeUP, IF(AND($G$7), 5%*$H$7*(1+1%*L4), 0),\n  WSPlus, 1+(0.01*'Master Sheet'!R18),\n  Relic, 1+$L6,\n  Vault, 1+$L12,\n\n(Base +PerkFreeUP) * WSPlus * Relic * Vault)", 'WS Attack Levels needed', "=SUM('Master Sheet'!N3:N6) - SUM('Master Sheet'!D3:D6) + IF('Master Sheet'!B7,SUM('Master Sheet'!N7:N8) - SUM('Master Sheet'!D7:D8)) + IF('Master Sheet'!B9,SUM('Master Sheet'!N9:N10) - SUM('Master Sheet'!D9:D10)) + IF('Master Sheet'!B11,SUM('Master Sheet'!N11:N12) - SUM('Master Sheet'!D11:D12)) + IF('Master Sheet'!B13,SUM('Master Sheet'!N13:N15) - SUM('Master Sheet'!D13:D15)) + IF('Master Sheet'!B16,SUM('Master Sheet'!N16:N17) - SUM('Master Sheet'!D16:D17)) + IF('Master Sheet'!B18,SUM('Master Sheet'!N18:N19) - SUM('Master Sheet'!D18:D19))", 'Lab', 'Standard Perks Bonus', "='Master Sheet'!Z7"]
- Formula cells: 23 (scanned 221 cells)
- Top formulas (up to 10):
  - =LET(
  Base,LET(
    WS,0%+'Master Sheet'!D42*0.5%,
    Cards, IF(ISNUMBER(L5), 3% + L5 * 1%, 0),
    Substat, $L9,
    WS + Cards + Substat),
  PerkFreeUP, IF(AND($G$7), 5%*$H$7*(1+1%*L4), 0),
  WSPlus, 1+(0.01*'Master Sheet'!R18),
  Relic, 1+$L6,
  Vault, 1+$L12,

(Base +PerkFreeUP) * WSPlus * Relic * Vault) (count=1)
  - =SUM('Master Sheet'!N3:N6) - SUM('Master Sheet'!D3:D6) + IF('Master Sheet'!B7,SUM('Master Sheet'!N7:N8) - SUM('Master Sheet'!D7:D8)) + IF('Master Sheet'!B9,SUM('Master Sheet'!N9:N10) - SUM('Master Sheet'!D9:D10)) + IF('Master Sheet'!B11,SUM('Master Sheet'!N11:N12) - SUM('Master Sheet'!D11:D12)) + IF('Master Sheet'!B13,SUM('Master Sheet'!N13:N15) - SUM('Master Sheet'!D13:D15)) + IF('Master Sheet'!B16,SUM('Master Sheet'!N16:N17) - SUM('Master Sheet'!D16:D17)) + IF('Master Sheet'!B18,SUM('Master Sheet'!N18:N19) - SUM('Master Sheet'!D18:D19)) (count=1)
  - ='Master Sheet'!Z7 (count=1)
  - =LET(
  Base,LET(
    WS,0%+'Master Sheet'!D42*0.5%,
    Cards, IF(ISNUMBER(L5), 3% + L5 * 1%, 0),
    Substat, $L10,
    WS+Cards+Substat),
  PerkFreeUP, IF(AND($G$7), 5%*$H$7*(1+1%*L4), 0),
  WSPlus, 1+(0.01*'Master Sheet'!R18),
  Relic, 1+$L7,
  Vault, 1+$L13,

(Base +PerkFreeUP) * WSPlus * Relic * Vault) (count=1)
  - =SUM('Master Sheet'!N20:N21)-SUM('Master Sheet'!D20:D21) + IF('Master Sheet'!B22,SUM('Master Sheet'!N22:N23) - SUM('Master Sheet'!D22:D23)) + IF('Master Sheet'!B24,SUM('Master Sheet'!N24) - SUM('Master Sheet'!D24))+ IF('Master Sheet'!B25,SUM('Master Sheet'!N25) - SUM('Master Sheet'!D25))+ IF('Master Sheet'!B26,SUM('Master Sheet'!N26:N27) - SUM('Master Sheet'!D26:D27))+ IF('Master Sheet'!B28,SUM('Master Sheet'!N28:N29) - SUM('Master Sheet'!D28:D29)) + IF('Master Sheet'!B30,SUM('Master Sheet'!N30:N31) - SUM('Master Sheet'!D30:D31)) + IF('Master Sheet'!B32,SUM('Master Sheet'!N32:N34) - SUM('Master Sheet'!D32:D34)) + IF('Master Sheet'!B35,SUM('Master Sheet'!N35) - SUM('Master Sheet'!D35)) + IF('Master Sheet'!B36,SUM('Master Sheet'!N36:N37) - SUM('Master Sheet'!D36:D37)) (count=1)
  - =IF(
  COUNTIF('Master Sheet'!AC4:AC30
, "Free Upgrades") > 0
, 'Master Sheet'!Z26, "No used") (count=1)
  - =LET(
  Base,LET(
    WS,0%+'Master Sheet'!D42*0.5%,
    Cards, IF(ISNUMBER(L5), 3% + L5 * 1%, 0),
    Substat, $L11,
    WS+Cards+Substat),
  PerkFreeUP, IF(AND($G$7), 5%*$H$7*(1+1%*L4), 0),
  WSPlus, 1+(0.01*'Master Sheet'!R18),
  Relic, 1+$L8,
  Vault, 1+$L14,

(Base +PerkFreeUP) * WSPlus * Relic * Vault) (count=1)
  - =IF('Master Sheet'!B38,SUM('Master Sheet'!N38:N39) - SUM('Master Sheet'!D38:D39)) + IF('Master Sheet'!B40,SUM('Master Sheet'!N40:N41) - SUM('Master Sheet'!D40:D41)) + IF('Master Sheet'!B42,SUM('Master Sheet'!N42:N44) - SUM('Master Sheet'!D42:D44)) + IF('Master Sheet'!B45,SUM('Master Sheet'!N45) - SUM('Master Sheet'!D45)) + IF('Master Sheet'!B46,SUM('Master Sheet'!N46:N48) - SUM('Master Sheet'!D46:D48)) + IF('Master Sheet'!B49,SUM('Master Sheet'!N49:N50) - SUM('Master Sheet'!D49:D50)) (count=1)
  - ='Master Sheet'!Z11 (count=1)
  - ='Master Sheet'!Z12 (count=1)
- Preview (first 5 rows × 10 cols):
  - [None, None, None, None, None, None, None, None, None, None]
  - [None, 'Interactive Gold Box Calculator\nCalculates, at which wave your WS will be gold boxed, without spending cash', None, None, None, None, None, None, None, 'Override this, if you want to use user\n specific inputs']
  - [None, None, None, None, None, None, None, None, None, None]
  - [None, 'Free Attack Upgrade', None, "=LET(\n  Base,LET(\n    WS,0%+'Master Sheet'!D42*0.5%,\n    Cards, IF(ISNUMBER(L5), 3% + L5 * 1%, 0),\n    Substat, $L9,\n    WS + Cards + Substat),\n  PerkFreeUP, IF(AND($G$7), 5%*$H$7*(1+1%*L4), 0),\n  WSPlus, 1+(0.01*'Master Sheet'!R18),\n  Relic, 1+$L6,\n  Vault, 1+$L12,\n\n(Base +PerkFreeUP) * WSPlus * Relic * Vault)", 'WS Attack Levels needed', None, "=SUM('Master Sheet'!N3:N6) - SUM('Master Sheet'!D3:D6) + IF('Master Sheet'!B7,SUM('Master Sheet'!N7:N8) - SUM('Master Sheet'!D7:D8)) + IF('Master Sheet'!B9,SUM('Master Sheet'!N9:N10) - SUM('Master Sheet'!D9:D10)) + IF('Master Sheet'!B11,SUM('Master Sheet'!N11:N12) - SUM('Master Sheet'!D11:D12)) + IF('Master Sheet'!B13,SUM('Master Sheet'!N13:N15) - SUM('Master Sheet'!D13:D15)) + IF('Master Sheet'!B16,SUM('Master Sheet'!N16:N17) - SUM('Master Sheet'!D16:D17)) + IF('Master Sheet'!B18,SUM('Master Sheet'!N18:N19) - SUM('Master Sheet'!D18:D19))", None, None, 'Lab']
  - [None, 'Free Defense Upgrade', None, "=LET(\n  Base,LET(\n    WS,0%+'Master Sheet'!D42*0.5%,\n    Cards, IF(ISNUMBER(L5), 3% + L5 * 1%, 0),\n    Substat, $L10,\n    WS+Cards+Substat),\n  PerkFreeUP, IF(AND($G$7), 5%*$H$7*(1+1%*L4), 0),\n  WSPlus, 1+(0.01*'Master Sheet'!R18),\n  Relic, 1+$L7,\n  Vault, 1+$L13,\n\n(Base +PerkFreeUP) * WSPlus * Relic * Vault)", 'WS Defense Levels needed', None, "=SUM('Master Sheet'!N20:N21)-SUM('Master Sheet'!D20:D21) + IF('Master Sheet'!B22,SUM('Master Sheet'!N22:N23) - SUM('Master Sheet'!D22:D23)) + IF('Master Sheet'!B24,SUM('Master Sheet'!N24) - SUM('Master Sheet'!D24))+ IF('Master Sheet'!B25,SUM('Master Sheet'!N25) - SUM('Master Sheet'!D25))+ IF('Master Sheet'!B26,SUM('Master Sheet'!N26:N27) - SUM('Master Sheet'!D26:D27))+ IF('Master Sheet'!B28,SUM('Master Sheet'!N28:N29) - SUM('Master Sheet'!D28:D29)) + IF('Master Sheet'!B30,SUM('Master Sheet'!N30:N31) - SUM('Master Sheet'!D30:D31)) + IF('Master Sheet'!B32,SUM('Master Sheet'!N32:N34) - SUM('Master Sheet'!D32:D34)) + IF('Master Sheet'!B35,SUM('Master Sheet'!N35) - SUM('Master Sheet'!D35)) + IF('Master Sheet'!B36,SUM('Master Sheet'!N36:N37) - SUM('Master Sheet'!D36:D37))", None, None, 'Card']

### Sheet: ELS+ ROI Calculator
- Dimensions: None rows × None cols
- First non-empty header-like row: 2
- Header values (non-empty): ['Interactive ELS vs ELS+ RoI Calculator\nCalculates the best Return on Investment for ELS and ELS+ Investments', '=AVERAGE(K1:K2)', '=IFERROR(VLOOKUP("Enemy Health Level Skip",IDS_MOD_GENERATOR_SUBSTATS(\'Master Sheet\'!AG38),4, FALSE), 0)+IFERROR(VLOOKUP("Enemy Health Level Skip",IDS_MOD_GENERATOR_SUBSTATS(\'Master Sheet\'!AG44),4, FALSE), 0)*\'Master Sheet\'!AG49']
- Formula cells: 15725 (scanned 20000 cells - truncated)
- Top formulas (up to 10):
  - =SUM($O$12:$O$710) (count=2)
  - =SUM($P$12:$P$710) (count=2)
  - =SUM($Q$12:$Q$710) (count=2)
  - =SUM($R$12:$R$710) (count=2)
  - =SUM($S$12:$S$710) (count=2)
  - =SUM($T$12:$T$710) (count=2)
  - =SUM($U$12:$U$710) (count=2)
  - =SUM($V$12:$V$710) (count=2)
  - =SUM($W$12:$W$710) (count=2)
  - =SUM($X$12:$X$710) (count=2)
- Preview (first 5 rows × 10 cols):
  - [None, None, None, None, None, None, None, None, None, 'Actual Sub']
  - [None, 'Interactive ELS vs ELS+ RoI Calculator\nCalculates the best Return on Investment for ELS and ELS+ Investments', None, None, None, None, None, None, None, '=AVERAGE(K1:K2)']
  - [None, None, None, None, None, None, None, None, None, 'ELS+']
  - [None, 'Vault enhancement discount', None, "='Master Sheet'!Z18", 'Utility discount lab lvl', None, "='Master Sheet'!Z4", None, None, None]
  - [None, 'ELS Vault', None, "=AVERAGE('Master Sheet'!Z22:AA23)", 'ELS Relics', None, "=AVERAGE('Master Sheet'!Z14:AA15)", None, None, None]

### Sheet: Coins+ vs ELS+
- Dimensions: None rows × None cols
- First non-empty header-like row: 3
- Header values (non-empty): ['User inputs', 'Results', 'Next coin price', <openpyxl.worksheet.formula.ArrayFormula object at 0x7ff58300cd60>, 'Avg WS ELS', 'Total EHLS -ELS+', '="% increase per " & FORMAT_NUMBER(N7)']
- Formula cells: 47 (scanned 442 cells)
- Top formulas (up to 10):
  - ="% increase per " & FORMAT_NUMBER(N7) (count=2)
  - <openpyxl.worksheet.formula.ArrayFormula object at 0x7ff58300e5c0> (count=1)
  - ="Coins+ "&P3 (count=1)
  - <openpyxl.worksheet.formula.ArrayFormula object at 0x7ff58300d810> (count=1)
  - =(IF(D4, D6,1)*(C21+((C23-C21)*0.67))/IF(D4,(D5*C23),1)+IF(D4,(((D5-D6)*C23)/(D5*699)),0))*IF(D4,C23,1) (count=1)
  - =
IF(D7="Health (GC)", G17+(M4*0.05%)+G19+(G21*0.1%)+G23,
G16+(M5*0.05%)+G18+(G20*0.1%)+G22
) (count=1)
  - =((((C17+1)/100+1)/(C17/100+1)-1)*2)/(J3/N7) (count=1)
  - =P4 (count=1)
  - =(IF(D4, D6,1)*(C20+((C22-C20)*0.67))/IF(D4,(D5*C22),1)+IF(D4,(((D5-D6)*C22)/(D5*C22)),0))*IF(D4,699,1) (count=1)
  - =IF(IDS_CARDS_IN_PRESET('Master Sheet'!AC3, "Intro Sprint"),IDS_LAB_LEVEL("Intro Sprint Mastery"),-1) (count=1)
- Preview (first 5 rows × 10 cols):
  - [None, None, None, None, None, None, None, None, None, None]
  - [None, None, None, None, None, None, None, None, None, None]
  - [None, 'User inputs', None, None, None, 'Results', None, None, 'Next coin price', <openpyxl.worksheet.formula.ArrayFormula object at 0x7ff58300e080>]
  - [None, 'Can you max ELS mid run?', None, True, None, '="Coins+ "&P3', None, None, 'Next els price', <openpyxl.worksheet.formula.ArrayFormula object at 0x7ff58300dde0>]
  - [None, 'At what wave do you die?', None, 10000.0, None, '=P4', None, None, None, None]

### Sheet: DVT_Workshop
- Dimensions: None rows × None cols
- First non-empty header-like row: 1
- Header values (non-empty): ['Damage', 'Health', 'Health Regen', 'Defense Absolute', 'Damage / Meter', 'Lifesteal', 'Damage', 'Rend Armor', 'Critical Factor', 'Damage/Meter', 'Super Crit Mult', 'Attack Speed', 'Health', 'Health Regen', 'Defense Absolute', 'Land Mine Damage', 'Wall Health', 'Orb Size', 'Cash Bonus', 'Coin Bonus', 'Cells / Kill Bonus', 'Free Upgrades', 'Recovery Package', 'Enemy Level Skips']
- Formula cells: 0 (scanned 20000 cells - truncated)
- Preview (first 5 rows × 10 cols):
  - [None, 'Damage', 'Health', 'Health Regen', 'Defense Absolute', 'Damage / Meter', 'Lifesteal', None, 'Damage', 'Rend Armor']
  - ['Workshop', 3.0, 5.0, 0.0005, 0.0, 0.0, 0.0, 'Workshop +', 0.0, 0.0]
  - [None, 5.877, 10.0, 0.0399999991059303, 0.504999995231628, 0.7939773798, 0.09927235544, None, 5000000000.0, 5000000000.0]
  - [None, 8.908, 15.0769996643066, 0.0884999982118607, 1.51994898564816, 1.576000094, 0.1970999986, None, 5040000000.0, 5040000000.0]
  - [None, 12.093, 20.097185602328, 0.151587081611156, 2.55563557463949, 2.346203089, 0.2934987247, None, 5110000000.0, 5110000000.0]

### Sheet: EXPORT
- Dimensions: None rows × None cols
- First non-empty header-like row: 2
- Header values (non-empty): ['U', 'Workshop Upgrade', "='Master Sheet'!D1", "='Master Sheet'!F1", "='Master Sheet'!H1", "='Master Sheet'!J1", "='Master Sheet'!L1", 'Workshop Enhancement', "='Master Sheet'!R1", "='Master Sheet'!S1", "='Master Sheet'!T1", "='Master Sheet'!U1", "='Master Sheet'!V1", '=FORMAT_NUMBER(WSPATTACK_TOTAL_COINS_INVESTED()+WSPDEFENSE_TOTAL_COINS_INVESTED()+WSPUTILITY_TOTAL_COINS_INVESTED())']
- Formula cells: 686 (scanned 1248 cells)
- Top formulas (up to 10):
  - ='Master Sheet'!D1 (count=1)
  - ='Master Sheet'!F1 (count=1)
  - ='Master Sheet'!H1 (count=1)
  - ='Master Sheet'!J1 (count=1)
  - ='Master Sheet'!L1 (count=1)
  - ='Master Sheet'!R1 (count=1)
  - ='Master Sheet'!S1 (count=1)
  - ='Master Sheet'!T1 (count=1)
  - ='Master Sheet'!U1 (count=1)
  - ='Master Sheet'!V1 (count=1)
- Preview (first 5 rows × 10 cols):
  - ['Wv2', None, None, None, None, None, None, None, None, None]
  - [None, 'U', 'Workshop Upgrade', "='Master Sheet'!D1", None, "='Master Sheet'!F1", None, "='Master Sheet'!H1", None, "='Master Sheet'!J1"]
  - [None, None, None, '¢ Level', '$ Level', '¢ Level', '$ Level', '¢ Level', '$ Level', '¢ Level']
  - [None, None, 'Damage', "='Master Sheet'!D3", "='Master Sheet'!E3", "='Master Sheet'!F3", "='Master Sheet'!G3", "='Master Sheet'!H3", "='Master Sheet'!I3", "='Master Sheet'!J3"]
  - [None, None, 'Attack Speed', "='Master Sheet'!D4", "='Master Sheet'!E4", "='Master Sheet'!F4", "='Master Sheet'!G4", "='Master Sheet'!H4", "='Master Sheet'!I4", "='Master Sheet'!J4"]
- EXPORT columns (23): ['Wv2', 'Unnamed: 1', 'Unnamed: 2', 'Unnamed: 3', 'Unnamed: 4', 'Unnamed: 5', 'Unnamed: 6', 'Unnamed: 7', 'Unnamed: 8', 'Unnamed: 9', 'Unnamed: 10', 'Unnamed: 11', 'Unnamed: 12', 'Unnamed: 13', 'Unnamed: 14', 'Unnamed: 15', 'Unnamed: 16', 'Unnamed: 17', 'Unnamed: 18', 'Unnamed: 19', 'Unnamed: 20', 'Unnamed: 21', 'Unnamed: 22']
- EXPORT row count: 50

### Sheet: Workshop Enhancement Prices
- Dimensions: None rows × None cols
- First non-empty header-like row: 1
- Header values (non-empty): ['Damage', 'Rend Armor', 'Critical Factor', 'Damage/Meter', 'Super Crit Mult', 'Attack Speed', 'Health', 'Health Regen', 'Defense Absolute', 'Land Mine Damage', 'Wall Health', 'Orb Size', 'Cash Bonus', 'Coin Bonus', 'Cells / Kill Bonus', 'Free Upgrades', 'Recovery Package', 'Enemy Level Skip']
- Formula cells: 0 (scanned 7638 cells)
- Preview (first 5 rows × 10 cols):
  - [None, 'Damage', 'Rend Armor', 'Critical Factor', 'Damage/Meter', 'Super Crit Mult', 'Attack Speed', 'Health', 'Health Regen', 'Defense Absolute']
  - ['Workshop +', 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0]
  - [None, 5000000000.0, 5000000000.0, 5000000000.0, 5000000000.0, 5000000000.0, 5000000000.0, 5000000000.0, 5000000000.0, 5000000000.0]
  - [None, 5040000000.0, 5040000000.0, 5040000000.0, 5040000000.0, 5040000000.0, 6100000000.0, 5040000000.0, 5040000000.0, 5040000000.0]
  - [None, 5110000000.0, 5110000000.0, 5110000000.0, 5110000000.0, 5110000000.0, 23580000000.0, 5110000000.0, 5110000000.0, 5110000000.0]
