import json, csv, re
import pandas as pd

bom = json.load(open('/home/paul22iac/projects/active/haven_dev_board_kicad/extracted/bom.json'))

xlsx_path = '/home/paul22iac/projects/active/haven_workspace/hardware/openearable_base_pcb/OpenEarable-PCB-main-2.0/OpenEarable-PCB-main-2.0-BOM.xlsx'
df = pd.read_excel(xlsx_path)

# explode xlsx by designator
xlsx_by_des = {}
for _, row in df.iterrows():
    designators = [d.strip() for d in str(row['Designator']).split(',')]
    for des in designators:
        xlsx_by_des[des] = row

def base_name_of(name):
    return re.sub(r"\.\d+$", "", name or "")

WEB_VERIFIED = {
    'J1': {
        'Manufacturer': 'Samtec', 'MPN': 'CLE-107-01-G-DV',
        'Note': 'Not present in OpenEarable\'s own BOM or the .epro export attrs either. '
                'Confirmed via web search (distributor listings: Newark/Arrow/Mouser/DigiKey/SnapEDA) '
                'as a real Samtec CLE-series 14-position 0.8mm-pitch board-to-board receptacle, '
                'matching the exact designation used in the schematic (\"CLE-107-01-G-DV\").'
    },
    'MDBT531': {
        'Manufacturer': 'Raytac', 'MPN': 'MDBT53-1M',
        'Note': 'Not present in OpenEarable\'s own BOM or the .epro export attrs (both just say '
                '"MDBT53" with no suffix). Confirmed via the OpenEarable 2.0 project\'s own published '
                'paper (Kolo et al., "OpenEarable 2.0: Open-Source Earphone Platform for Physiological '
                'Ear Sensing", MIT/ACM IMWUT), which explicitly states "RAYTAC MDBT53-1M module" '
                '(external/formal antenna variant, not the -P1M PCB-antenna variant).'
    },
}

rows = []
tier_counts = {1: 0, 2: 0, 3: 0, 4: 0}

# representative MPNs for generic passives lacking any real sourced MPN --
# only used as a last resort, real manufacturer/real part number/real
# matching value+package+tolerance, clearly labeled.
REPRESENTATIVE = {
    ('R', '0201'): ('Yageo', 'RC0201FR-07{val}L'),
    ('R', '0402'): ('Yageo', 'RC0402FR-07{val}L'),
    ('C', '0201'): ('Murata', 'GRM033R71{val}'),
    ('C', '0402'): ('Murata', 'GRM155R71{val}'),
    ('L', '0402'): ('TDK', 'MLZ1005{val}'),
}

for des in sorted(bom.keys(), key=lambda d: (re.match(r'[A-Za-z]+', d).group(0), int(re.search(r'\d+', d).group(0)) if re.search(r'\d+', d) else 0)):
    c = bom[des]
    attrs = c['attrs']
    value = base_name_of(c['name'])
    footprint_of = attrs.get('Origin Footprint', '')
    xlsx_row = xlsx_by_des.get(des)

    mfr = attrs.get('Manufacturer') or None
    mpn = attrs.get('Manufacturer Part') or None
    supplier = attrs.get('Supplier') or None
    supplier_part = attrs.get('Supplier Part') or None
    source = None
    notes = ''

    if mpn:
        source = 2  # per-designator port/.epro attrs
    elif xlsx_row is not None and pd.notna(xlsx_row.get('Manufacturer Part')):
        mfr = xlsx_row['Manufacturer']
        mpn = xlsx_row['Manufacturer Part']
        supplier = xlsx_row.get('Supplier')
        supplier_part = xlsx_row.get('Supplier Part')
        source = 1  # OpenEarable's own official BOM
    elif des in WEB_VERIFIED:
        mfr = WEB_VERIFIED[des]['Manufacturer']
        mpn = WEB_VERIFIED[des]['MPN']
        notes = WEB_VERIFIED[des]['Note']
        source = 1  # treated as authoritative: real, independently confirmed sourced part
    else:
        prefix = re.match(r'[A-Za-z]+', des).group(0)
        pkg_match = re.search(r'(0201|0402|0603)', footprint_of)
        pkg = pkg_match.group(0) if pkg_match else None
        key = (prefix, pkg)
        if key in REPRESENTATIVE and value:
            rep_mfr, template = REPRESENTATIVE[key]
            mfr = rep_mfr
            mpn = f"[representative example, value={value}, not sourced from original design]"
            source = 3
            notes = 'Generic passive; no MPN in OpenEarable BOM, port data, or found via web search. ' \
                    f'A real {rep_mfr} part exists in this value/package family but the exact ' \
                    'MPN was not independently looked up digit-for-digit -- treat as illustrative only.'
        else:
            source = 4
            notes = 'No MPN found in OpenEarable\'s BOM, the .epro export attrs, or via web search.'

    if des == 'U1' and value.upper() == 'BMX160' and mpn == 'BMI160':
        notes = ('DISCREPANCY IN SOURCE DATA (not introduced by this port): the schematic\'s own '
                 'component value/comment says "BMX160" (Bosch 9-axis IMU incl. magnetometer), but '
                 'the sourced Manufacturer Part in OpenEarable\'s own official BOM is "BMI160" '
                 '(Bosch 6-axis IMU, accel+gyro only, NO magnetometer) -- a genuinely different real '
                 'part. Worth confirming which was actually populated before assuming magnetometer '
                 'data is available.')

    tier_counts[source] += 1
    source_label = {
        1: 'OpenEarable official BOM / web-verified real part',
        2: 'Port data (.epro Manufacturer Part attr)',
        3: 'Representative/example MPN -- NOT sourced from original design',
        4: 'Needs sourcing',
    }[source]

    raw_name = attrs.get('Name', '')
    xlsx_comment = xlsx_row['Comment'] if (xlsx_row is not None and pd.notna(xlsx_row.get('Comment'))) else None
    xlsx_value = xlsx_row['Value'] if (xlsx_row is not None and pd.notna(xlsx_row.get('Value'))) else None
    if not raw_name or raw_name.startswith('='):
        # port's own Name attr is missing or an unevaluated EasyEDA formula
        # ("={Value}") -- prefer the official xlsx's human-readable Comment/
        # Value field, then fall back to the port-derived value string.
        description = xlsx_comment or xlsx_value or value
        if xlsx_value:
            value = xlsx_value
    else:
        description = raw_name

    rows.append({
        'Reference': des,
        'Description': description,
        'Value': value,
        'Package/Footprint': footprint_of,
        'Manufacturer': mfr or '',
        'MPN': mpn or '',
        'Source': source_label,
        'Qty': 1,
        'Notes': notes,
    })

out_path = '/home/paul22iac/projects/active/haven_dev_board_kicad/HAVEN_BOM.csv'
with open(out_path, 'w', newline='') as f:
    w = csv.DictWriter(f, fieldnames=['Reference', 'Description', 'Value', 'Package/Footprint', 'Manufacturer', 'MPN', 'Source', 'Qty', 'Notes'])
    w.writeheader()
    for r in rows:
        w.writerow(r)

print('Wrote', out_path, 'with', len(rows), 'lines')
print('Tier breakdown:', tier_counts)
print('Tier 4 (needs sourcing) designators:', [r['Reference'] for r in rows if r['Source'] == 'Needs sourcing'])
print('Tier 3 (representative) designators:', [r['Reference'] for r in rows if 'Representative' in r['Source']])

# ---- regroup into one row per unique (value, footprint, mfr, mpn) combo ----
from collections import OrderedDict
groups = OrderedDict()
for r in rows:
    key = (r['Description'], r['Value'], r['Package/Footprint'], r['Manufacturer'], r['MPN'], r['Source'], r['Notes'])
    groups.setdefault(key, []).append(r['Reference'])

def des_sort_key(d):
    m = re.match(r'([A-Za-z]+)(\d+)?', d)
    return (m.group(1), int(m.group(2)) if m.group(2) else 0)

grouped_rows = []
for key, refs in groups.items():
    desc, value, pkg, mfr, mpn, source, notes = key
    refs_sorted = sorted(refs, key=des_sort_key)
    grouped_rows.append({
        'Reference': ','.join(refs_sorted),
        'Description': desc, 'Value': value, 'Package/Footprint': pkg,
        'Manufacturer': mfr, 'MPN': mpn, 'Source': source,
        'Qty': len(refs_sorted), 'Notes': notes,
    })

grouped_rows.sort(key=lambda r: des_sort_key(r['Reference'].split(',')[0]))

with open(out_path, 'w', newline='') as f:
    w = csv.DictWriter(f, fieldnames=['Reference', 'Description', 'Value', 'Package/Footprint', 'Manufacturer', 'MPN', 'Source', 'Qty', 'Notes'])
    w.writeheader()
    for r in grouped_rows:
        w.writerow(r)

print('\nGrouped into', len(grouped_rows), 'BOM lines (from 89 individual designators)')
