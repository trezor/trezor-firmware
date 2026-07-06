use anyhow::{Context, Result};
use std::{
    collections::{HashMap, HashSet},
    path::PathBuf,
};

pub fn zero_symnames<I, S>(elf_path: &PathBuf, keep_names: I, verbose: bool) -> Result<()>
where
    I: IntoIterator<Item = S>,
    S: AsRef<str>,
{
    let keep_names: HashSet<String> = keep_names
        .into_iter()
        .map(|s| s.as_ref().to_string())
        .collect();

    let mut data = std::fs::read(elf_path)
        .with_context(|| format!("Failed to read ELF: {}", elf_path.display()))?;

    anyhow::ensure!(&data[..4] == b"\x7fELF", "Not an ELF file");
    anyhow::ensure!(data[4] == 1, "Only 32-bit ELF supported");
    let little = data[5] == 1;

    macro_rules! u16 {
        ($off:expr) => {
            if little {
                u16::from_le_bytes(data[$off..$off + 2].try_into().unwrap())
            } else {
                u16::from_be_bytes(data[$off..$off + 2].try_into().unwrap())
            }
        };
    }
    macro_rules! u32 {
        ($off:expr) => {
            if little {
                u32::from_le_bytes(data[$off..$off + 4].try_into().unwrap())
            } else {
                u32::from_be_bytes(data[$off..$off + 4].try_into().unwrap())
            }
        };
    }
    macro_rules! put_u32 {
        ($data:expr, $off:expr, $val:expr) => {
            let bytes = if little {
                ($val as u32).to_le_bytes()
            } else {
                ($val as u32).to_be_bytes()
            };
            $data[$off..$off + 4].copy_from_slice(&bytes);
        };
    }

    let e_shoff = u32!(32) as usize;
    let e_shentsize = u16!(46) as usize;
    let e_shnum = u16!(48) as usize;
    let e_shstrndx = u16!(50) as usize;

    #[derive(Clone)]
    struct Shdr {
        sh_type: u32,
        sh_offset: usize,
        sh_size: usize,
        _sh_link: u32,
        sh_info: u32,
        sh_entsize: usize,
        index: usize,
    }

    let sections: Vec<Shdr> = (0..e_shnum)
        .map(|i| {
            let off = e_shoff + i * e_shentsize;
            Shdr {
                sh_type: u32!(off + 4),
                sh_offset: u32!(off + 16) as usize,
                sh_size: u32!(off + 20) as usize,
                _sh_link: u32!(off + 24),
                sh_info: u32!(off + 28),
                sh_entsize: u32!(off + 36) as usize,
                index: i,
            }
        })
        .collect();

    let symtab = sections
        .iter()
        .find(|s| s.sh_type == 2)
        .context("Cannot find .symtab")?
        .clone();
    let strtab = sections
        .iter()
        .find(|s| s.sh_type == 3 && s.index != e_shstrndx)
        .context("Cannot find .strtab")?
        .clone();
    let rel_sections: Vec<Shdr> = sections
        .iter()
        .filter(|s| s.sh_type == 9)
        .cloned()
        .collect();

    let strtab_off = strtab.sh_offset;
    let strtab_size = strtab.sh_size;
    let symtab_off = symtab.sh_offset;
    let sym_size = symtab.sh_entsize;
    let sym_count = symtab.sh_size / sym_size;
    let first_global = symtab.sh_info as usize;

    let get_str = |name_off: usize| -> String {
        if name_off == 0 {
            return String::new();
        }
        let start = strtab_off + name_off;
        let end = data[start..].iter().position(|&b| b == 0).unwrap_or(0) + start;
        String::from_utf8_lossy(&data[start..end]).into_owned()
    };

    #[derive(Clone)]
    struct Sym {
        st_value: u32,
        st_size: u32,
        st_info: u8,
        st_other: u8,
        st_shndx: u16,
        name: String,
        new_name_off: u32,
    }

    let get_sym = |i: usize| -> Sym {
        let off = symtab_off + i * sym_size;
        let st_name = u32!(off);
        Sym {
            st_value: u32!(off + 4),
            st_size: u32!(off + 8),
            st_info: data[off + 12],
            st_other: data[off + 13],
            st_shndx: u16!(off + 14),
            name: get_str(st_name as usize),
            new_name_off: 0,
        }
    };

    let mut referenced_syms: HashSet<usize> = HashSet::new();
    for rel_sec in &rel_sections {
        let rel_count = rel_sec.sh_size / 8;
        for j in 0..rel_count {
            let info = u32!(rel_sec.sh_offset + j * 8 + 4);
            referenced_syms.insert((info >> 8) as usize);
        }
    }

    for i in 0..sym_count {
        let sym = get_sym(i);
        if keep_names.contains(sym.name.as_str()) {
            referenced_syms.insert(i);
        }
    }
    referenced_syms.insert(0);

    let mut old_to_new: HashMap<usize, usize> = HashMap::new();
    let mut new_syms: Vec<Sym> = Vec::new();

    for i in 0..first_global {
        if referenced_syms.contains(&i) {
            old_to_new.insert(i, new_syms.len());
            new_syms.push(get_sym(i));
        }
    }
    let new_first_global = new_syms.len();
    for i in first_global..sym_count {
        if referenced_syms.contains(&i) {
            old_to_new.insert(i, new_syms.len());
            new_syms.push(get_sym(i));
        }
    }

    let mut new_strtab: Vec<u8> = vec![0];
    for sym in &mut new_syms {
        if !sym.name.is_empty() && keep_names.contains(sym.name.as_str()) {
            sym.new_name_off = new_strtab.len() as u32;
            new_strtab.extend_from_slice(sym.name.as_bytes());
            new_strtab.push(0);
        } else {
            sym.new_name_off = 0;
        }
    }

    for rel_sec in &rel_sections {
        let rel_count = rel_sec.sh_size / 8;
        for j in 0..rel_count {
            let info_off = rel_sec.sh_offset + j * 8 + 4;
            let info = u32!(info_off);
            let old_sym_idx = (info >> 8) as usize;
            let rel_type = info & 0xFF;
            let new_sym_idx = *old_to_new
                .get(&old_sym_idx)
                .with_context(|| format!("Relocation references unknown symbol {old_sym_idx}"))?;
            let new_info = ((new_sym_idx as u32) << 8) | rel_type;
            put_u32!(data, info_off, new_info);
        }
    }

    let new_symtab_size = new_syms.len() * sym_size;
    let old_symtab_size = symtab.sh_size;
    for (i, sym) in new_syms.iter().enumerate() {
        let off = symtab_off + i * sym_size;
        put_u32!(data, off, sym.new_name_off);
        put_u32!(data, off + 4, sym.st_value);
        put_u32!(data, off + 8, sym.st_size);
        data[off + 12] = sym.st_info;
        data[off + 13] = sym.st_other;
        let shndx_bytes = if little {
            sym.st_shndx.to_le_bytes()
        } else {
            sym.st_shndx.to_be_bytes()
        };
        data[off + 14..off + 16].copy_from_slice(&shndx_bytes);
    }
    data[symtab_off + new_symtab_size..symtab_off + old_symtab_size].fill(0);

    let old_strtab_size = strtab_size;
    let new_strtab_len = new_strtab.len();
    data[strtab_off..strtab_off + new_strtab_len].copy_from_slice(&new_strtab);
    data[strtab_off + new_strtab_len..strtab_off + old_strtab_size].fill(0);

    let set_shdr_u32 = |data: &mut Vec<u8>, idx: usize, field_off: usize, val: u32| {
        let off = e_shoff + idx * e_shentsize + field_off;
        let bytes = if little {
            val.to_le_bytes()
        } else {
            val.to_be_bytes()
        };
        data[off..off + 4].copy_from_slice(&bytes);
    };

    set_shdr_u32(&mut data, symtab.index, 20, new_symtab_size as u32);
    set_shdr_u32(&mut data, symtab.index, 28, new_first_global as u32);
    set_shdr_u32(&mut data, strtab.index, 20, new_strtab_len as u32);

    std::fs::write(elf_path, &data)
        .with_context(|| format!("Failed to write ELF: {}", elf_path.display()))?;

    if verbose {
        let symtab_saved = old_symtab_size - new_symtab_size;
        let strtab_saved = old_strtab_size - new_strtab_len;
        println!(
            "zero_symnames: symtab: {sym_count} -> {} symbols ({old_symtab_size} -> {new_symtab_size} bytes, saved {symtab_saved})",
            new_syms.len()
        );
        println!(
            "zero_symnames: strtab: {old_strtab_size} -> {new_strtab_len} bytes (saved {strtab_saved})"
        );
        println!(
            "zero_symnames: total saved: {} bytes",
            symtab_saved + strtab_saved
        );

        let found_names: HashSet<&str> = new_syms
            .iter()
            .filter(|s| keep_names.contains(s.name.as_str()))
            .map(|s| s.name.as_str())
            .collect();
        println!("zero_symnames: kept named symbols: {:?}", found_names);

        let missing: Vec<&str> = keep_names
            .iter()
            .map(|s| s.as_str())
            .filter(|n| !found_names.contains(n))
            .collect();
        if !missing.is_empty() {
            eprintln!("WARNING: requested symbols not found: {:?}", missing);
        }
    }

    Ok(())
}
