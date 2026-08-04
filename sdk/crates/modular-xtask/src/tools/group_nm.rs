use anyhow::Result;
use regex::Regex;
use std::collections::HashMap;
use std::io::{BufRead, Cursor, Write};
use std::path::Path;
use std::process::{Command, Stdio};

#[derive(Default)]
struct Node {
    bytes: usize,
    children: HashMap<String, Node>,
    sym: Option<(usize, usize, String)>,
}

impl Node {
    fn new() -> Self {
        Self::default()
    }
}

fn unwrap_impl(sym: &str) -> String {
    if !sym.starts_with('<') {
        return sym.to_string();
    }
    let mut depth = 0usize;
    for (i, c) in sym.char_indices() {
        match c {
            '<' => depth += 1,
            '>' => {
                depth -= 1;
                if depth == 0 {
                    let inner = &sym[1..i];
                    let rest = &sym[i + 1..];
                    let inner = if let Some(pos) = inner.find(" as ") {
                        &inner[..pos]
                    } else {
                        inner
                    };
                    return format!("{inner}{rest}");
                }
            }
            _ => {}
        }
    }
    sym.to_string()
}

fn split_path(sym: &str, hash_re: &Regex) -> Vec<String> {
    let sym = hash_re.replace(sym.trim(), "").to_string();
    let sym = unwrap_impl(&sym);
    let mut parts = Vec::new();
    let mut depth = 0usize;
    let mut current = String::new();
    let chars: Vec<char> = sym.chars().collect();
    let mut i = 0;
    while i < chars.len() {
        let c = chars[i];
        match c {
            '<' => {
                depth += 1;
                current.push(c);
            }
            '>' => {
                depth -= 1;
                current.push(c);
            }
            ':' if i + 1 < chars.len() && chars[i + 1] == ':' && depth == 0 => {
                if !current.is_empty() {
                    parts.push(current.clone());
                    current.clear();
                }
                i += 2;
                continue;
            }
            _ => current.push(c),
        }
        i += 1;
    }
    if !current.is_empty() {
        parts.push(current);
    }
    parts
}

fn decompose_symbol(
    binary: &str,
    addr: usize,
    size: usize,
    outermost: &str,
    depth: usize,
    addr2line: &str,
    step: usize,
) -> Option<HashMap<String, usize>> {
    let addr_input: String = (addr..addr + size)
        .step_by(step)
        .map(|a| format!("0x{a:x}\n"))
        .collect();

    let mut child = Command::new(addr2line)
        .args(["-i", "-f", "--demangle", "-e", binary])
        .stdin(Stdio::piped())
        .stdout(Stdio::piped())
        .stderr(Stdio::null())
        .spawn()
        .ok()?;

    let mut stdin = child.stdin.take()?;
    let input_bytes = addr_input.into_bytes();
    let writer = std::thread::spawn(move || stdin.write_all(&input_bytes));

    let output = child.wait_with_output().ok()?;
    let _ = writer.join();

    if !output.status.success() {
        return None;
    }

    let stdout = String::from_utf8_lossy(&output.stdout);
    let lines: Vec<&str> = stdout.lines().collect();
    let mut groups: HashMap<String, usize> = HashMap::new();
    let mut current_stack: Vec<&str> = Vec::new();
    let mut i = 0;

    while i + 1 < lines.len() {
        let func = lines[i].trim();
        i += 2;
        current_stack.push(func);

        if func == outermost {
            if current_stack.len() <= depth {
                *groups.entry("(self)".into()).or_default() += step;
            } else {
                let idx = current_stack.len() - 1 - depth;
                *groups.entry(current_stack[idx].to_string()).or_default() += step;
            }
            current_stack.clear();
        }
    }

    if !current_stack.is_empty() {
        *groups.entry("(unknown)".into()).or_default() += current_stack.len() / 2 * step;
    }

    if groups.is_empty() {
        None
    } else {
        Some(groups)
    }
}

fn decompose_leaves(
    binary: &str,
    root: &mut Node,
    decompose_min: usize,
    decompose_depth: usize,
    addr2line: &str,
) {
    let mut stack: Vec<Vec<String>> = vec![vec![]];

    while let Some(path) = stack.pop() {
        let node = path
            .iter()
            .fold(&mut *root, |n, key| n.children.get_mut(key).unwrap());

        let keys: Vec<String> = node.children.keys().cloned().collect();

        for key in keys {
            let child = node.children.get_mut(&key).unwrap();

            if !child.children.is_empty() {
                let mut child_path = path.clone();
                child_path.push(key.clone());
                stack.push(child_path);
            } else if child.bytes >= decompose_min {
                if let Some((addr, size, full_name)) = child.sym.clone() {
                    if let Some(groups) = decompose_symbol(
                        binary,
                        addr,
                        size,
                        &full_name,
                        decompose_depth,
                        addr2line,
                        2,
                    ) {
                        if groups.len() > 1 {
                            for (inline_name, inline_bytes) in groups {
                                let mut inline_node = Node::new();
                                inline_node.bytes = inline_bytes;
                                child.children.insert(inline_name, inline_node);
                            }
                        }
                    }
                }
            }
        }
    }
}

fn yaml_key(name: &str) -> String {
    let special = Regex::new(r#"[:{}<>\[\],&*?|!%@`#'"\\]"#).unwrap();
    if special.is_match(name) || name.starts_with('-') {
        format!("\"{}\"", name.replace('\\', "\\\\").replace('"', "\\\""))
    } else {
        name.to_string()
    }
}

fn print_tree(node: &Node, indent: usize, total: usize, min_print_size: usize) {
    let prefix = "  ".repeat(indent);
    let mut children: Vec<(&String, &Node)> = node
        .children
        .iter()
        .filter(|(_, c)| c.bytes >= min_print_size)
        .collect();
    children.sort_by(|a, b| b.1.bytes.cmp(&a.1.bytes));

    let modules: Vec<_> = children
        .iter()
        .filter(|(_, c)| !c.children.is_empty())
        .cloned()
        .collect();
    let leaves: Vec<_> = children
        .iter()
        .filter(|(_, c)| c.children.is_empty())
        .cloned()
        .collect();

    if !modules.is_empty() && !leaves.is_empty() {
        let self_bytes: usize = leaves.iter().map(|(_, c)| c.bytes).sum();
        let self_pct = self_bytes as f64 * 100.0 / total as f64;

        let mut all_entries: Vec<(String, usize)> = modules
            .iter()
            .map(|(n, c)| (n.to_string(), c.bytes))
            .collect();
        all_entries.push(("(self)".into(), self_bytes));
        all_entries.sort_by(|a, b| b.1.cmp(&a.1));

        for (name, bytes) in &all_entries {
            if name == "(self)" {
                println!("{prefix}(self):  # {self_bytes} bytes, {self_pct:.1}%");
                for (lname, lchild) in &leaves {
                    let lpct = lchild.bytes as f64 * 100.0 / total as f64;
                    println!(
                        "{prefix}  {}: {}  # {lpct:.1}%",
                        yaml_key(lname),
                        lchild.bytes
                    );
                }
            } else {
                let pct = *bytes as f64 * 100.0 / total as f64;
                println!("{prefix}{}:  # {bytes} bytes, {pct:.1}%", yaml_key(name));
                if let Some(child) = node.children.get(name.as_str()) {
                    print_tree(child, indent + 1, total, min_print_size);
                }
            }
        }
    } else {
        for (name, child) in modules.iter().chain(leaves.iter()) {
            let pct = child.bytes as f64 * 100.0 / total as f64;
            let key = yaml_key(name);
            if !child.children.is_empty() {
                println!("{prefix}{key}:  # {} bytes, {pct:.1}%", child.bytes);
                print_tree(child, indent + 1, total, min_print_size);
            } else {
                println!("{prefix}{key}: {}  # {pct:.1}%", child.bytes);
            }
        }
    }
}

pub fn group_nm(
    input: &[u8],
    binary: Option<&Path>,
    min_print_size: usize,
    decompose_min: usize,
    decompose_depth: usize,
    addr2line: &str,
) -> Result<()> {
    let line_re = Regex::new(r"^\s*([0-9a-fA-F]+)\s+([0-9a-fA-F]+)\s+([A-Za-z])\s+(.+)$").unwrap();
    let hash_re = Regex::new(r"::h[0-9a-f]{16}$").unwrap();

    let mut root = Node::new();

    for line in Cursor::new(input).lines() {
        let line = line?;
        let Some(caps) = line_re.captures(&line) else {
            continue;
        };
        let (addr_hex, size_hex, typ, sym) = (&caps[1], &caps[2], &caps[3], &caps[4]);
        if !"tTwWrRdD".contains(typ) {
            continue;
        }
        if sym.starts_with(".L") {
            continue;
        }

        let size = usize::from_str_radix(size_hex, 16)?;
        let addr = usize::from_str_radix(addr_hex, 16)?;
        let parts = split_path(sym, &hash_re);

        root.bytes += size;
        let mut node = &mut root;
        for part in &parts {
            node = node.children.entry(part.clone()).or_default();
            node.bytes += size;
        }
        node.sym = Some((addr, size, sym.to_string()));
    }

    let total = root.bytes.max(1);

    if let Some(binary) = binary {
        if binary.is_file() {
            decompose_leaves(
                binary.to_str().unwrap(),
                &mut root,
                decompose_min,
                decompose_depth,
                addr2line,
            );
        }
    }

    println!("# Total: {total} bytes, min display: {min_print_size} bytes");
    print_tree(&root, 0, total, min_print_size);

    Ok(())
}
