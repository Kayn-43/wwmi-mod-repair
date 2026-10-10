#!/usr/bin/env python3
"""Read-only comparison of namespaced WWMI Before/After texture traces."""
import argparse
from collections import defaultdict
import json
from pathlib import Path
import re
import struct

from audit_mod import first, load_ini, local_path, parse_sections, sha


def descriptor(text):
    size = re.search(r'width=(\d+) height=(\d+)', text)
    fmt = re.search(r'format="([^"]+)"', text)
    return {'dimensions': list(map(int, size.groups())) if size else None,
            'format': fmt[1] if fmt else None}


def resource_size(path):
    if not path or not path.is_file():
        return None
    with path.open('rb') as stream:
        head = stream.read(128)
    if head[:4] == b'DDS ' and len(head) == 128:
        height, width = struct.unpack_from('<II', head, 12)
        return [width, height]
    try:
        from PIL import Image
        with Image.open(path) as image:
            return list(image.size)
    except (ImportError, OSError, ValueError):
        return None


def read_frame(path, namespace, before, after, mesh, ranges):
    log = path / 'log.txt'
    log_hash = sha(log)
    text = log.read_text(encoding='utf-8', errors='replace')
    calls = defaultdict(list)
    current = None
    for line in text.splitlines():
        match = re.match(r'(\d{6}) ', line)
        if match:
            current = match[1]
        if current:
            calls[current].append(line)
    pattern = re.compile(r'(\d{6}).*?\[TextureOverride_' + re.escape(namespace) +
                         r'_(' + re.escape(before) + '|' + re.escape(after) +
                         r')\]-ps-t(\d+)(?:=([\da-f]{8})(?:\(([\da-f]{8})\))?)?\.dsc$', re.I)
    phases = defaultdict(lambda: defaultdict(dict))
    inputs = {str(log): log_hash}
    for file in path.glob('*.dsc'):
        match = pattern.match(file.name)
        if not match:
            continue
        call, phase, slot, h, original = match.groups()
        canonical_phase = 'before' if phase.casefold() == before.casefold() else 'after'
        if slot in phases[call][canonical_phase]:
            raise ValueError('Duplicate trace descriptor for call/phase/slot: ' + file.name)
        inputs[str(file)] = sha(file)
        desc = file.read_text(encoding='utf-8')
        phases[call][canonical_phase][slot] = dict(descriptor(desc), hash=h, original_hash=original, file=file.name)
    draws, incomplete = [], []
    for call, phase in sorted(phases.items()):
        block = '\n'.join(calls[call])
        native = re.search(r'^\d{6} DrawIndexed\(IndexCount:(\d+), StartIndexLocation:(\d+), BaseVertexLocation:(-?\d+)\)', block, re.M)
        shader_files = list(path.glob(call + '-vb0=' + mesh + '-*.buf'))
        shaders = sorted({re.search(r'-vs=([\da-f]+)-ps=([\da-f]+)', f.name).groups()
                          for f in shader_files if re.search(r'-vs=([\da-f]+)-ps=([\da-f]+)', f.name)})
        if not native or set(phase) != {'before', 'after'} or not shaders:
            incomplete.append({'call': call, 'reason': 'Missing native draw, phase or native mesh shader dump'})
            continue
        native_range = tuple(map(int, native.groups()))
        component = ranges.get(native_range[:2], set())
        if len(component) != 1:
            incomplete.append({'call': call, 'reason': 'Unknown or ambiguous component range'})
            continue
        draws.append({'call': call, 'component': next(iter(component)), 'native_range': list(native_range),
                      'shaders': shaders, 'phases': dict(phase)})
    return {'path': str(path), 'draws': draws, 'incomplete_draws': incomplete,
            'native_draw_count': len(re.findall(r'^\d{6} DrawIndexed\(', text, re.M)),
            'abort_marker_present': 'Frame analysis aborted' in text, 'input_hashes': inputs}


def compare(old, new, mappings, resources):
    def groups(frame):
        result = defaultdict(list)
        for draw in frame['draws']:
            key = (draw['component'], tuple(draw['native_range']), tuple(map(tuple, draw['shaders'])))
            result[key].append(draw)
        return result
    aa, bb = groups(old), groups(new)
    candidates, rejected, unmatched = defaultdict(list), [], []
    for key in aa.keys() | bb.keys():
        a, b = aa.get(key, []), bb.get(key, [])
        if not a or len(a) != len(b):
            unmatched.append({'component': key[0], 'native_range': key[1], 'shaders': key[2],
                              'abnormal_count': len(a), 'normal_count': len(b)})
            continue
        for x, y in zip(a, b):
            for slot, low in x['phases']['before'].items():
                high = y['phases']['before'].get(slot)
                if not high or not low['hash'] or low['hash'] == high['hash']:
                    continue
                proof = {'component': x['component'], 'slot': int(slot), 'abnormal_hash': low['hash'],
                         'normal_hash': high['hash'], 'abnormal_call': x['call'], 'normal_call': y['call'],
                         'native_range': x['native_range'], 'shaders': x['shaders'], 'abnormal': low, 'normal': high}
                targets = mappings.get(high['hash'], set())
                lower_targets = mappings.get(low['hash'], set())
                reason = None
                if lower_targets:
                    reason = 'Existing abnormal-hash rule needs runtime condition review'
                elif len(targets) != 1:
                    reason = 'Normal hash has no unique local Resource mapping'
                elif slot not in x['phases']['after'] or slot not in y['phases']['after']:
                    reason = 'Missing after descriptor'
                else:
                    low_after, high_after = x['phases']['after'][slot], y['phases']['after'][slot]
                    signature = lambda d: (d['hash'], d['dimensions'], d['format'])
                    resource = next(iter(targets))
                    proof.update(resource=resource, normal_after=high_after, resource_info=resources[resource])
                    if signature(low) != signature(low_after):
                        reason = 'Abnormal input already changed during callbacks'
                    elif signature(high) == signature(high_after):
                        reason = 'Normal input also not replaced'
                    elif not low['format'] or low['format'] != high['format']:
                        reason = 'Native input formats differ or unavailable'
                    elif not low['dimensions'] or not high['dimensions'] or not all(h >= l for l, h in zip(low['dimensions'], high['dimensions'])) or low['dimensions'] == high['dimensions']:
                        reason = 'Not a demonstrated lower-resolution input'
                    elif resources[resource]['dimensions'] is None or resources[resource]['dimensions'] != high_after['dimensions']:
                        reason = 'Normal after dimensions do not verify mapped resource'
                if reason:
                    rejected.append(dict(proof, reason=reason))
                else:
                    candidates[(x['component'], int(slot), low['hash'])].append(proof)
    accepted = []
    for proofs in candidates.values():
        if len({p['resource'] for p in proofs}) != 1:
            rejected.extend(dict(p, reason='Conflicting resource targets for same component/slot/hash') for p in proofs)
        else:
            accepted.append(dict(proofs[0], supporting_calls=[[p['abnormal_call'], p['normal_call']] for p in proofs]))
    return accepted, rejected, unmatched


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for flag in ['ini', 'abnormal', 'normal', 'output']:
        parser.add_argument('--' + flag, type=Path, required=True)
    parser.add_argument('--trace-namespace', required=True)
    parser.add_argument('--before', default='Before')
    parser.add_argument('--after', default='After')
    parser.add_argument('--mesh-hash')
    parser.add_argument('--mod-root', type=Path, help='Resource root when the baseline INI is a backup outside its Mod')
    parser.add_argument('--encoding', default='utf-8')
    args = parser.parse_args()
    mod_root = (args.mod_root or args.ini.parent).resolve(strict=True)
    out = args.output.resolve()
    if any(part.casefold() == 'mods' for part in out.parts) or out.is_relative_to(mod_root):
        parser.error('Output must be outside Mod and WWMI Mods tree')
    text, ini_info = load_ini(args.ini, args.encoding)
    sections = parse_sections(text)
    components = [s for s in sections if s['name'].lower().startswith('textureoverride') and first(s, 'match_index_count') and first(s, 'match_first_index') and first(s, 'hash')]
    meshes = {first(s, 'hash').lower() for s in components}
    mesh = args.mesh_hash.lower() if args.mesh_hash else next(iter(meshes)) if len(meshes) == 1 else None
    if mesh not in meshes:
        parser.error('Specify a mesh hash matching the desired component overrides')
    ranges = defaultdict(set)
    for s in components:
        if first(s, 'hash').lower() == mesh:
            ranges[(int(first(s, 'match_index_count')), int(first(s, 'match_first_index')))].add(s['name'])
    resources = {}
    resource_inputs = {}
    for s in sections:
        filename = first(s, 'filename')
        if s['name'].lower().startswith('resource') and filename:
            name = s['name'].lower()
            path = local_path(mod_root, filename)
            if path and path.is_file():
                resource_inputs[str(path)] = sha(path)
            info = {'filename': filename, 'dimensions': resource_size(path)}
            if name in resources and resources[name] != info:
                parser.error('Ambiguous duplicate Resource definition: ' + s['name'])
            resources[name] = info
    mappings = defaultdict(set)
    for s in sections:
        h = first(s, 'hash')
        if not h:
            continue
        for key, value in s['entries']:
            if key.lower() == 'this' and value.lower() in resources:
                mappings[h.lower()].add(value.lower())
    old = read_frame(args.abnormal, args.trace_namespace, args.before, args.after, mesh, ranges)
    new = read_frame(args.normal, args.trace_namespace, args.before, args.after, mesh, ranges)
    accepted, rejected, unmatched = compare(old, new, mappings, resources)
    unchanged = sha(args.ini) == ini_info['sha256'] and all(sha(Path(path)) == h for frame in [old, new] for path, h in frame['input_hashes'].items()) and all(sha(Path(path)) == h for path, h in resource_inputs.items())
    if not unchanged:
        raise RuntimeError('Input changed during analysis; discard this result')
    status = 'INVALID_CAPTURE_NO_TARGET_DRAWS' if not old['draws'] or not new['draws'] else 'CANDIDATE_EVIDENCE_REQUIRES_REVIEW'
    result = {'state': status, 'ini': ini_info, 'mesh_hash': mesh, 'abnormal_frame': old, 'normal_frame': new,
              'candidate_bindings': accepted, 'excluded_changes': rejected, 'unmatched_groups': unmatched,
              'source_unchanged': unchanged, 'resource_input_hashes': resource_inputs, 'limitations': 'Static local INI subset and identical VS/PS only. No include/condition simulation or causal proof; does not install repairs.'}
    out.mkdir(parents=True, exist_ok=True)
    (out / 'texture-frame-comparison.json').write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding='utf-8')
    print(f"{status}: {len(old['draws'])}/{len(new['draws'])} target draws, {len(accepted)} candidate bindings, {len(unmatched)} unmatched groups.")


if __name__ == '__main__':
    main()
