#!/usr/bin/env python3
"""Parse IL2CPP metadata v31 extracted from Umamusume Pretty Derby (JP).

The metadata is embedded in GameAssembly.dll .data at RVA 0x07E242C0 and was
recovered by overwriting the first 8 bytes (sanity + version) with the standard
values 0xFAB11BAF / 31. See docs/05 for the full derivation.

Usage:
    python parse_metadata_v31.py metadata_jp_recovered.dat

Outputs namespace/type statistics and optionally a full type listing.
"""
import struct
import sys
import collections

TABLE_NAMES = [
    'stringLiteral', 'stringLiteralData', 'string', 'events', 'properties', 'methods',
    'parameterDefaultValues', 'fieldDefaultValues', 'fieldAndParameterDefaultValueData',
    'fieldMarshaledSizes', 'parameters', 'fields', 'genericParameters',
    'genericParameterConstraints', 'genericContainers', 'nestedTypes', 'interfaces',
    'vtableMethods', 'interfaceOffsets', 'typeDefinitions', 'images', 'assemblies',
    'fieldRefs', 'referencedAssemblies', 'attributeData', 'attributeDataRange',
    'unresolvedVirtualCallParameters', 'unresolvedVirtualCallStubs',
    'windowsRuntimeTypeNames', 'windowsRuntimeStrings', 'exportedTypeDefinitions',
]

TD_STRIDE = 0x58          # sizeof(Il2CppTypeDefinition) in v31
SANITY = 0xFAB11BAF


class Metadata:
    def __init__(self, path):
        self.blob = open(path, 'rb').read()
        if len(self.blob) < 0x100:
            raise ValueError('file too small')
        self.hdr = struct.unpack_from('<64I', self.blob, 0)
        if self.hdr[0] != SANITY:
            raise ValueError('bad sanity 0x%08x (expected 0x%08x)' % (self.hdr[0], SANITY))
        if self.hdr[1] != 31:
            raise ValueError('unsupported version %d (expected 31)' % self.hdr[1])
        self.tables = {}
        for i, nm in enumerate(TABLE_NAMES):
            self.tables[nm] = (self.hdr[2 + i * 2], self.hdr[3 + i * 2])
        self.str_off = self.tables['string'][0]

    def string(self, idx):
        if idx < 0:
            return ''
        end = self.blob.find(b'\x00', self.str_off + idx)
        if end < 0:
            return ''
        return self.blob[self.str_off + idx:end].decode('utf-8', 'replace')

    def type_count(self):
        return self.tables['typeDefinitions'][1] // TD_STRIDE

    def type_at(self, i):
        """Return dict for the i-th Il2CppTypeDefinition."""
        base = self.tables['typeDefinitions'][0] + i * TD_STRIDE
        name_idx, ns_idx = struct.unpack_from('<ii', self.blob, base)
        byval, byref, decl, parent = struct.unpack_from('<4i', self.blob, base + 8)
        # v31 实际布局（实测校准）：
        #   +0x18 elementTypeIndex  +0x1C genericContainerIndex
        #   +0x20 fieldStart        +0x24 methodStart
        #   +0x28 eventStart        +0x2C propertyStart
        #   +0x30 nestedTypesStart  +0x34 interfacesStart
        #   +0x38 vtableStart       +0x3C interfaceOffsetsStart
        elem, gencont, field_start, method_start = struct.unpack_from(
            '<4i', self.blob, base + 0x18)
        flags = struct.unpack_from('<I', self.blob, base + 0x1C)[0]
        mc, pc, fc, ec, ntc, vt, ic, ioc = struct.unpack_from('<8H', self.blob, base + 0x40)
        bitfield = struct.unpack_from('<I', self.blob, base + 0x54)[0]
        return {
            'index': i,
            'name': self.string(name_idx),
            'namespace': self.string(ns_idx),
            'parent': parent,
            'flags': flags,
            'method_start': method_start,
            'method_count': mc,
            'field_start': field_start,
            'field_count': fc,
            'property_count': pc,
            'event_count': ec,
            'nested_type_count': ntc,
            'vtable_count': vt,
            'interfaces_count': ic,
            'bitfield': bitfield,
        }


def main():
    path = sys.argv[1] if len(sys.argv) > 1 else 'metadata_jp_recovered.dat'
    m = Metadata(path)
    n = m.type_count()
    print('metadata: %d bytes, version 31, %d types' % (len(m.blob), n))

    ns_counter = collections.Counter()
    gallop = 0
    for i in range(n):
        t = m.type_at(i)
        ns_counter[t['namespace']] += 1
        if t['namespace'].startswith('Gallop'):
            gallop += 1

    print('\n=== namespace distribution (top 20) ===')
    for ns, c in ns_counter.most_common(20):
        print('  %-52s %6d' % (ns or '(global)', c))
    print('\nGallop.* types: %d (%.1f%%)' % (gallop, 100.0 * gallop / n))

    print('\n=== first 10 type definitions ===')
    for i in range(10):
        t = m.type_at(i)
        print('  #%-4d %-36s %-32s methods=%d fields=%d'
              % (i, t['namespace'][:34], t['name'][:30], t['method_count'], t['field_count']))


if __name__ == '__main__':
    main()
