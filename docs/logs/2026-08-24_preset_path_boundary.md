# Preset Path Write Boundary

**Date:** 2026-08-24  
**Scope:** decoded image, track-relative `+0x453F`

The stable spatial map already bounded the preset identity string at
`+0x453F..+0x456E`. The next byte, `+0x456F`, is the count prefix for the
pattern's note vector. Therefore the fixed preset path field is exactly 48
bytes and can contain at most 47 non-null Latin-1 bytes.

The structural reader and image writer previously used a 64-byte window. Real
device strings were short enough that reads appeared correct, but a writer
call with a long path could overwrite note count/data. `ImageProject` now owns
the 48-byte constant; the inspector and generated-project validator share it.
Regression coverage verifies null padding and rejects 48-byte input before any
note-vector byte can be changed.
