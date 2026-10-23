from pathlib import Path

path = Path(__file__).resolve().parents[1] / 'apps/web/src/main.tsx'
content = path.read_text(encoding='utf-8')
old = '<Field label="PDF file · maximum 10 MiB">'
new = '''<Field label="Supersede previous evidence (optional)"><select name="supersedes_id"><option value="">Add new evidence</option>{selected.documents.filter(d => d.active).map(d => <option value={d.id} key={d.id}>{d.category} · {short(d.id)}</option>)}</select></Field><Field label="PDF file · maximum 10 MiB">'''
if old in content and 'Supersede previous evidence' not in content:
    content = content.replace(old, new)
content = content.replace('<Badge value={d.status}/></div><small className="hash">', '<Badge value={d.active ? d.status : \'SUPERSEDED\'}/></div><small className="hash">')
path.write_text(content, encoding='utf-8')
