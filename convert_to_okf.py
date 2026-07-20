"""Convert legend_classification.json to OKF bundle format."""
import json
import os
from pathlib import Path


def main():
    base = Path(__file__).parent
    okf_dir = base / "okf"
    classes_dir = okf_dir / "classes"
    classes_dir.mkdir(parents=True, exist_ok=True)

    with open(base / "assets" / "legend_classification.json") as f:
        data = json.load(f)

    legend = data["legend_classification"]
    metadata = legend["metadata"]
    classes = legend["classes"]

    # Root index
    index_lines = [
        "# P&ID Symbol Ontology",
        "",
        f"Total parent classes: {metadata['total_classes']}",
        f"Total subclasses: {metadata['total_subclasses']}",
        f"Source: {metadata['source']}",
        "",
        "## Parent Classes",
        "",
    ]
    for name in classes:
        index_lines.append(f"- [{name}](classes/{name.lower()}.md)")
    index_lines.append("")

    (okf_dir / "index.md").write_text("\n".join(index_lines))

    # Per-class concept files
    for name, info in classes.items():
        subs = info["subclasses"]
        count = len(subs)
        slug = name.lower().replace(" ", "_")

        lines = [
            "---",
            f"type: P&ID Parent Class",
            f"title: \"{name}\"",
            f"description: \"{count} symbol subclasses in the {name} category.\"",
            f"tags: [pid, ontology, {slug}]",
            "---",
            "",
            f"# {name}",
            "",
            f"**Subclass count:** {count}",
            "",
            "## Subclasses",
            "",
        ]
        for sub in subs:
            display = sub.replace("_", " ")
            lines.append(f"- {display}")

        lines.append("")
        lines.append("---")
        lines.append("")
        lines.append("## Schema")
        lines.append("")
        lines.append("| Field | Value |")
        lines.append("|-------|-------|")
        lines.append(f"| parent_class | {name} |")
        lines.append(f"| subclass_count | {count} |")
        lines.append(f"| concept_id | classes/{slug} |")
        lines.append("")

        (classes_dir / f"{slug}.md").write_text("\n".join(lines))

    print(f"OKF bundle created at {okf_dir}")
    print(f"  index.md + {len(classes)} class files")


if __name__ == "__main__":
    main()
