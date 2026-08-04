use anyhow::Result;
pub fn print_elf_sections(output: &std::process::Output) -> Result<()> {
    anyhow::ensure!(output.status.success(), "readelf failed");

    let flag_map: &[(&str, &str)] = &[
        ("W", "write"),
        ("A", "alloc"),
        ("X", "exec"),
        ("M", "merge"),
        ("S", "strings"),
        ("I", "info"),
        ("L", "link-order"),
        ("O", "OS-proc"),
        ("G", "group"),
        ("T", "TLS"),
        ("C", "compressed"),
        ("E", "exclude"),
        ("D", "mbind"),
        ("y", "purecode"),
        ("p", "proc-specific"),
    ];

    let re = regex::Regex::new(
        r"\s*\[\s*\d+\]\s+(\S+)\s+(\S+)\s+\S+\s+\S+\s+([0-9a-fA-F]+)\s+\S+\s*(\S*)",
    )?;

    println!("  {:<18} {:<16} {:>12}  Flags", "Name", "Type", "Size");
    println!(
        "  {} {} {}  {}",
        "-".repeat(18),
        "-".repeat(16),
        "-".repeat(12),
        "-".repeat(20)
    );

    for line in String::from_utf8_lossy(&output.stdout).lines() {
        if let Some(caps) = re.captures(line) {
            let name = &caps[1];
            let typ = &caps[2];
            let size = usize::from_str_radix(&caps[3], 16)?;
            let flags = &caps[4];

            let size_str = format_number(size);
            let flag_names: Vec<&str> = flags
                .chars()
                .map(|c| {
                    flag_map
                        .iter()
                        .find(|(k, _)| k.chars().next() == Some(c))
                        .map(|(_, v)| *v)
                        .unwrap_or("?")
                })
                .collect();

            println!(
                "  {:<18} {:<16} {:>12}  {}",
                name,
                typ,
                size_str,
                flag_names.join(" ")
            );
        }
    }

    Ok(())
}

fn format_number(n: usize) -> String {
    let s = n.to_string();
    let mut result = String::new();
    for (i, c) in s.chars().rev().enumerate() {
        if i > 0 && i % 3 == 0 {
            result.push(',');
        }
        result.push(c);
    }
    result.chars().rev().collect()
}
