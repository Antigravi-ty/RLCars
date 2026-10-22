import struct, base64, zlib
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes

default_key = bytes([
    0xC7, 0xDF, 0x6B, 0x13, 0x25, 0x2A, 0xCC, 0x71,
    0x47, 0xBB, 0x51, 0xC9, 0x8A, 0xD7, 0xE3, 0x4B,
    0x7F, 0xE5, 0x00, 0xB7, 0x7F, 0xA5, 0xFA, 0xB2,
    0x93, 0xE2, 0xF2, 0x4E, 0x6B, 0x17, 0xE7, 0x79
])

keys = [default_key]
with open("/tmp/aes.txt", "r") as f:
    for line in f:
        line = line.strip()
        if line:
            keys.append(base64.b64decode(line))

def unpack_rl_upk(in_path, out_path):
    with open(in_path, "rb") as f:
        data = f.read()
    pos = 0
    def r_i32():
        nonlocal pos
        v = struct.unpack_from("<i", data, pos)[0]
        pos += 4
        return v
    def r_u32():
        nonlocal pos
        v = struct.unpack_from("<I", data, pos)[0]
        pos += 4
        return v
    def r_u16():
        nonlocal pos
        v = struct.unpack_from("<H", data, pos)[0]
        pos += 2
        return v
    def r_i64():
        nonlocal pos
        v = struct.unpack_from("<q", data, pos)[0]
        pos += 8
        return v
    def r_fstr():
        nonlocal pos
        length = r_i32()
        if length < 0:
            length = -length
            s = data[pos:pos+length*2].decode("utf-16-le", errors="replace").rstrip("\x00")
            pos += length*2
        elif length > 0:
            s = data[pos:pos+length].decode("latin1", errors="replace").rstrip("\x00")
            pos += length
        else:
            s = ""
        return s

    tag = r_u32()
    file_ver = r_u16()
    lic_ver = r_u16()
    total_header_size = r_i32()
    folder_name = r_fstr()
    pkg_flags_offset = pos
    pkg_flags = r_u32()
    name_count = r_i32()
    name_offset = r_i32()
    export_count = r_i32()
    export_offset = r_i32()
    import_count = r_i32()
    import_offset = r_i32()
    depends_offset = r_i32()
    import_export_guids_offset = r_i32()
    import_guids_count = r_i32()
    export_guids_count = r_i32()
    thumbnail_table_offset = r_i32()
    guid = data[pos:pos+16]; pos += 16
    gen_count = r_i32()
    for _ in range(gen_count):
        r_i32(); r_i32(); r_i32()
    engine_ver = r_u32()
    cooker_ver = r_u32()
    comp_flags_offset = pos
    comp_flags = r_u32()
    chunk_count = r_i32()
    for _ in range(chunk_count):
        r_i64(); r_i32(); r_i64(); r_i32()
        if lic_ver >= 33:
            pos += 12
    unk5 = r_i32()
    add_pkg_count = r_i32()
    for _ in range(add_pkg_count):
        r_fstr()
    tex_alloc_count = r_i32()
    for _ in range(tex_alloc_count):
        r_i32(); r_i32(); r_i32(); r_i32(); r_i32()
        exp_idx_count = r_i32()
        pos += exp_idx_count * 4
    garbage_size = r_i32()
    compressed_chunks_offset = r_i32()
    last_block_size = r_i32()
    print(f"[{in_path}] pos={pos}, name_offset={name_offset}, total_header_size={total_header_size}, garbage_size={garbage_size}, chunks_off={compressed_chunks_offset}, last_blk={last_block_size}")

    enc_size = (total_header_size - garbage_size - name_offset + 15) & ~15
    enc_buf = data[name_offset:name_offset+enc_size]

    block_offset = compressed_chunks_offset % 16
    block_start = compressed_chunks_offset - block_offset
    test_slice = enc_buf[block_start:block_start+32]

    found_key = None
    for idx, k in enumerate(keys):
        cipher = Cipher(algorithms.AES(k), modes.ECB())
        dec = cipher.decryptor().update(test_slice)
        c_len = struct.unpack_from("<i", dec, block_offset)[0]
        uncomp_off = struct.unpack_from("<q", dec, block_offset+4)[0]
        if 1 <= c_len <= 1000 and uncomp_off == depends_offset:
            found_key = k
            print(f"  Found key at index {idx}: {base64.b64encode(k).decode()} (chunks={c_len}, first_uncomp={uncomp_off})")
            break
    if not found_key:
        raise RuntimeError("No key found!")

    cipher = Cipher(algorithms.AES(found_key), modes.ECB())
    dec_buf = cipher.decryptor().update(enc_buf)

    # Read compressed chunks from dec_buf at compressed_chunks_offset
    cpos = compressed_chunks_offset
    num_chunks = struct.unpack_from("<i", dec_buf, cpos)[0]; cpos += 4
    chunks = []
    for _ in range(num_chunks):
        u_off, u_size, c_off, c_size = struct.unpack_from("<qiqi", dec_buf, cpos)
        cpos += 24
        if lic_ver >= 33:
            cpos += 12
        chunks.append((u_off, u_size, c_off, c_size))
        print(f"  Chunk: uncomp={u_off}..{u_off+u_size} (size {u_size}), comp={c_off} (size {c_size})")

    out = bytearray(data[:name_offset])
    out.extend(dec_buf)
    # Truncate or pad to first chunk uncompressed offset
    first_u_off = chunks[0][0]
    if len(out) < first_u_off:
        out.extend(b"\x00" * (first_u_off - len(out)))
    else:
        out = out[:first_u_off]

    for u_off, u_size, c_off, c_size in chunks:
        assert len(out) == u_off, f"len(out)={len(out)} != u_off={u_off}"
        bpos = c_off
        magic, block_size, comp_total, uncomp_total = struct.unpack_from("<IIII", data, bpos)
        bpos += 16
        num_blocks = (uncomp_total + block_size - 1) // block_size
        blocks = []
        for _ in range(num_blocks):
            b_c_size, b_u_size = struct.unpack_from("<II", data, bpos)
            bpos += 8
            blocks.append((b_c_size, b_u_size))
        for b_c_size, b_u_size in blocks:
            decomp = zlib.decompress(data[bpos:bpos+b_c_size])
            assert len(decomp) == b_u_size
            out.extend(decomp)
            bpos += b_c_size

    # Reset PKG_Cooked (0x8) and CompressionFlags
    PKG_Cooked = 0x00000008
    struct.pack_into("<I", out, pkg_flags_offset, pkg_flags & ~PKG_Cooked)
    struct.pack_into("<I", out, comp_flags_offset, 0)

    with open(out_path, "wb") as f:
        f.write(out)
    print(f"  Wrote unpacked UPK to {out_path} ({len(out)} bytes)")

unpack_rl_upk("/tmp/triBody/triBody/body_thrice_SF.upk", "/tmp/body_thrice_SF_unpacked.upk")
unpack_rl_upk("/tmp/triBody/triBody/body_tritip_SF.upk", "/tmp/body_tritip_SF_unpacked.upk")
