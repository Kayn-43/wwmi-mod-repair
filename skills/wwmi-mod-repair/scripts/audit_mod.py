#!/usr/bin/env python3
"""Read-only WWMI audit. No inferred fixes, no execution of INI/HLSL content."""
import argparse
from collections import Counter
import difflib
import hashlib
import json
from pathlib import Path
import re
import struct


def sha(path):
    digest = hashlib.sha256()
    with path.open('rb') as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b''):
            digest.update(block)
    return digest.hexdigest()


def load_ini(path, encoding):
    raw = path.read_bytes()
    if raw.startswith((b'\xff\xfe\x00\x00', b'\x00\x00\xfe\xff')):
        codec = 'utf-32'
    elif raw.startswith((b'\xff\xfe', b'\xfe\xff')):
        codec = 'utf-16'
    elif raw.startswith(b'\xef\xbb\xbf'):
        codec = 'utf-8-sig'
    else:
        codec = encoding
    decoded = raw.decode(codec)
    text = decoded.replace('\r\n', '\n').replace('\r', '\n')
    info = {'path': str(path), 'sha256': sha(path), 'bytes': len(raw),
            'encoding': codec, 'crlf_count': decoded.count('\r\n')}
    return text, info


def parse_sections(text):
    found = list(re.finditer(r'^[ \t]*\[([^\]\r\n]+)\][ \t]*(?:;[^\r\n]*)?$', text, re.M))
    result = []
    occurrences = Counter()
    for index, match in enumerate(found):
        name = match[1].strip()
        occurrences[name.casefold()] += 1
        block = text[match.end():found[index + 1].start() if index + 1 < len(found) else len(text)]
        values = []
        for row in block.splitlines():
            line = row.strip()
            if not line or line.startswith(';') or '=' not in line:
                continue
            key, value = line.split('=', 1)
            values.append([key.strip(), value.partition(';')[0].strip()])
        result.append({'name': name, 'occurrence': occurrences[name.casefold()],
                       'line': text[:match.start()].count('\n') + 1, 'entries': values})
    return result


def first(section, key):
    return next((value for item, value in section['entries'] if item.casefold() == key.casefold()), None)


def local_path(root, filename):
    candidate = (root / filename.strip('"').replace('\\', '/')).resolve()
    return candidate if candidate.is_relative_to(root) else None


def inventory(root):
    return {p.relative_to(root).as_posix(): sha(p) for p in sorted(root.rglob('*'))
            if p.is_file() and p.resolve().is_relative_to(root)}


def delta(old, new):
    def keyed(items):
        return {(s['name'].casefold(), s['occurrence']): s for s in items}
    a, b = keyed(old), keyed(new)
    return {'added_sections': [b[k]['name'] for k in b.keys() - a.keys()],
            'removed_sections': [a[k]['name'] for k in a.keys() - b.keys()],
            'changed_sections': [{'name': b[k]['name'], 'occurrence': k[1],
                                  'before': a[k]['entries'], 'after': b[k]['entries']}
                                 for k in b if k in a and a[k]['entries'] != b[k]['entries']]}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--mod-root', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--compare', type=Path, action='append', default=[])
    parser.add_argument('--encoding', default='utf-8')
    args = parser.parse_args()
    root = args.mod_root.resolve(strict=True)
    output = args.output.resolve()
    if output.is_relative_to(root) or any(part.casefold() == 'mods' for part in output.parts):
        parser.error('Output must be outside the Mod and outside the default WWMI Mods tree.')
    current = root / 'mod.ini'
    if not current.resolve(strict=True).is_relative_to(root):
        parser.error('mod.ini resolves outside the selected Mod.')
    before_inventory = inventory(root)
    text, info = load_ini(current, args.encoding)
    sections = parse_sections(text)
    report = {'parser_scope': 'Static subset; no include/condition/shader simulation.',
              'root': str(root), 'current': info, 'sections': sections,
              'inventory': before_inventory, 'resources': [], 'comparisons': [],
              'buffer_backup_differences': [], 'components': []}
    resource_sections = {}
    for section in sections:
        filename = first(section, 'filename')
        if filename is None:
            continue
        path = local_path(root, filename)
        item = {'section': section['name'], 'filename': filename,
                'outside_root_not_read': path is None, 'exists': path.is_file() if path else None}
        if path is not None and path.is_file():
            item.update(bytes=path.stat().st_size, sha256=sha(path))
            if path.suffix.casefold() == '.dds':
                with path.open('rb') as stream:
                    header = stream.read(148)
                if len(header) >= 128 and header[:4] == b'DDS ':
                    height, width = struct.unpack_from('<II', header, 12)
                    fourcc = header[84:88].decode('ascii', errors='replace')
                    item['dds'] = {'width': width, 'height': height, 'fourcc': fourcc,
                                   'dxgi': struct.unpack_from('<I', header, 128)[0]
                                   if fourcc == 'DX10' and len(header) >= 148 else None}
            stride = first(section, 'stride')
            if stride and stride.isdigit():
                stride = int(stride)
                if stride > 0:
                    item.update(stride=stride, stride_entries=item['bytes'] // stride,
                                stride_remainder=item['bytes'] % stride)
            resource_sections[section['name'].casefold()] = (section, path)
        report['resources'].append(item)

    pair = resource_sections.get('resourceindexbuffer')
    indices = None
    if pair:
        section, path = pair
        fmt = (first(section, 'format') or '').upper().removeprefix('DXGI_FORMAT_')
        code = {'R32_UINT': 'I', 'R16_UINT': 'H'}.get(fmt)
        if code:
            raw = path.read_bytes()
            size = struct.calcsize('<' + code)
            if len(raw) % size == 0:
                indices = [v[0] for v in struct.iter_unpack('<' + code, raw)]
    vertex_match = re.search(r'(?im)^\s*global\s+\$mesh_vertex_count\s*=\s*(\d+)', text)
    vertex_count = int(vertex_match[1]) if vertex_match else None
    for section in sections:
        if not section['name'].casefold().startswith('textureoverridecomponent'):
            continue
        component = {'section': section['name'], 'draws': [], 'unique_vertices': None}
        refs = set()
        for key, value in section['entries']:
            if key.casefold() != 'drawindexed':
                continue
            if not re.fullmatch(r'\s*\d+\s*,\s*\d+\s*,\s*-?\d+\s*', value):
                component['draws'].append({'value': value, 'bounds_verified': False})
                continue
            count, start, base_vertex = map(int, value.split(','))
            draw = {'value': value, 'bounds_verified': False}
            if indices is not None:
                index_ok = start + count <= len(indices)
                vertices = {v + base_vertex for v in indices[start:start + count]} if index_ok else set()
                refs.update(vertices)
                draw.update(index_range_valid=index_ok, bounds_verified=index_ok and vertex_count is not None,
                            vertex_range_valid=(not vertices or min(vertices) >= 0 and max(vertices) < vertex_count)
                            if vertex_count is not None and index_ok else None)
            component['draws'].append(draw)
        if indices is not None:
            component.update(unique_vertices=len(refs), vertex_min=min(refs) if refs else None,
                             vertex_max=max(refs) if refs else None,
                             contiguous_vertex_set=len(refs) == max(refs) - min(refs) + 1 if refs else None)
        report['components'].append(component)

    for relative in before_inventory:
        path = root / relative
        if path.suffix.casefold() != '.buf':
            continue
        for backup in sorted(path.parent.glob(path.name + '*')):
            if backup == path or 'bak' not in backup.name.casefold() or not backup.is_file() or not backup.resolve().is_relative_to(root):
                continue
            a, b = path.read_bytes(), backup.read_bytes()
            report['buffer_backup_differences'].append({'current': relative, 'backup': backup.relative_to(root).as_posix(),
                'current_bytes': len(a), 'backup_bytes': len(b), 'same': a == b,
                'changed_byte_count': sum(x != y for x, y in zip(a, b)) + abs(len(a) - len(b))})

    diffs = []
    for index, path in enumerate(args.compare, 1):
        old_text, old_info = load_ini(path.resolve(strict=True), args.encoding)
        report['comparisons'].append({'input': old_info, 'changes': delta(parse_sections(old_text), sections)})
        diffs.append((f'comparison_{index}.diff', ''.join(difflib.unified_diff(
            old_text.splitlines(True), text.splitlines(True), fromfile=path.name, tofile='mod.ini'))))
    if inventory(root) != before_inventory:
        raise RuntimeError('Source changed during audit; retry with a stable baseline.')
    report['source_unchanged_during_audit'] = True
    output.mkdir(parents=True, exist_ok=True)
    (output / 'audit.json').write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
    for name, content in diffs:
        (output / name).write_text(content, encoding='utf-8', newline='\n')
    print(json.dumps({'sections': len(sections), 'resources': len(report['resources']),
                      'comparisons': len(diffs), 'report': str(output / 'audit.json'),
                      'source_unchanged': True}, ensure_ascii=False))


if __name__ == '__main__':
    main()
