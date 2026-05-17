import json
import os
import shutil
import subprocess
import tempfile
from typing import List


def _js_string(value: str) -> str:
    return json.dumps(value)


def generate_report_docx(job_id: str, results: List[dict], output_path: str) -> str:
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    js_path = os.path.join(tempfile.gettempdir(), f"{job_id}_report.js")
    results_json = json.dumps(results)
    output_path_js = _js_string(os.path.abspath(output_path))

    script = f"""
const {{
  Document, Packer, Paragraph, TextRun, Table, TableRow, TableCell,
  HeadingLevel, AlignmentType, BorderStyle, WidthType, ShadingType,
  LevelFormat, PageBreak
}} = require('docx');
const fs = require('fs');

const results = {results_json};
const outputPath = {output_path_js};
const tableWidth = 9360;
const columnWidths = [2800, 1200, 3200, 2160];

const border = {{
  style: BorderStyle.SINGLE,
  size: 1,
  color: 'CCCCCC'
}};

function text(value) {{
  return value === undefined || value === null ? '' : String(value);
}}

function cell(content, width, fill, bold = false) {{
  return new TableCell({{
    width: {{ size: width, type: WidthType.DXA }},
    margins: {{ top: 80, bottom: 80, left: 120, right: 120 }},
    borders: {{ top: border, bottom: border, left: border, right: border }},
    shading: fill ? {{ type: ShadingType.CLEAR, fill }} : undefined,
    children: [
      new Paragraph({{
        children: [new TextRun({{ text: text(content), bold }})]
      }})
    ]
  }});
}}

function codeParagraph(line, color, fill) {{
  return new Paragraph({{
    shading: {{ type: ShadingType.CLEAR, fill }},
    children: [
      new TextRun({{
        text: text(line),
        font: 'Courier New',
        size: 18,
        color
      }})
    ]
  }});
}}

function limitedCodeParagraphs(code, color, fill) {{
  const lines = text(code).split('\\n');
  const shown = lines.slice(0, 50).map((line) => codeParagraph(line, color, fill));
  if (lines.length > 50) {{
    shown.push(codeParagraph('... [truncated]', color, fill));
  }}
  return shown.length ? shown : [codeParagraph('', color, fill)];
}}

const summaryRows = [
  new TableRow({{
    children: [
      cell('File', columnWidths[0], 'D5E8F0', true),
      cell('Language', columnWidths[1], 'D5E8F0', true),
      cell('Changes', columnWidths[2], 'D5E8F0', true),
      cell('Status', columnWidths[3], 'D5E8F0', true)
    ]
  }}),
  ...results.map((result, index) => {{
    const fill = index % 2 === 0 ? 'FFFFFF' : 'F5F5F5';
    return new TableRow({{
      children: [
        cell(result.filename, columnWidths[0], fill),
        cell(result.language, columnWidths[1], fill),
        cell(result.changes_summary, columnWidths[2], fill),
        cell('✓ Modernized', columnWidths[3], fill)
      ]
    }});
  }})
];

const children = [
  new Paragraph({{ text: 'Legacy Whisperer — Modernization Report', heading: HeadingLevel.HEADING_1 }}),
  new Paragraph({{ text: 'Powered by IBM watsonx' }}),
  new Paragraph({{ text: `Total files modernized: ${{results.length}}` }}),
  new Paragraph({{ children: [new PageBreak()] }}),
  new Paragraph({{ text: 'Executive Summary', heading: HeadingLevel.HEADING_1 }}),
  new Table({{
    width: {{ size: tableWidth, type: WidthType.DXA }},
    columnWidths,
    rows: summaryRows
  }}),
  new Paragraph({{ children: [new PageBreak()] }})
];

results.forEach((result, index) => {{
  children.push(new Paragraph({{ text: `File: ${{text(result.filename)}}`, heading: HeadingLevel.HEADING_1 }}));
  children.push(new Paragraph({{ text: `Language: ${{text(result.language)}}`, heading: HeadingLevel.HEADING_2 }}));
  children.push(new Paragraph({{ text: 'Summary of Changes', heading: HeadingLevel.HEADING_2 }}));
  children.push(new Paragraph({{ text: text(result.changes_summary) }}));
  children.push(new Paragraph({{ text: 'Documentation', heading: HeadingLevel.HEADING_2 }}));
  children.push(new Paragraph({{ text: text(result.documentation) }}));
  children.push(new Paragraph({{ text: 'Original Code', heading: HeadingLevel.HEADING_2 }}));
  children.push(...limitedCodeParagraphs(result.original_code, '333333', 'F0F0F0'));
  children.push(new Paragraph({{ text: 'Modernized Code', heading: HeadingLevel.HEADING_2 }}));
  children.push(...limitedCodeParagraphs(result.modernized_code, '1A5276', 'EAF4FB'));
  if (index < results.length - 1) {{
    children.push(new Paragraph({{ children: [new PageBreak()] }}));
  }}
}});

const doc = new Document({{
  styles: {{
    default: {{
      document: {{
        run: {{ font: 'Arial', size: 24 }}
      }}
    }},
    paragraphStyles: [
      {{
        id: 'Heading1',
        name: 'Heading 1',
        basedOn: 'Normal',
        next: 'Normal',
        quickFormat: true,
        run: {{ font: 'Arial', bold: true, size: 32 }},
        paragraph: {{ spacing: {{ before: 240, after: 240 }}, outlineLevel: 0 }}
      }},
      {{
        id: 'Heading2',
        name: 'Heading 2',
        basedOn: 'Normal',
        next: 'Normal',
        quickFormat: true,
        run: {{ font: 'Arial', bold: true, size: 28 }},
        paragraph: {{ spacing: {{ before: 180, after: 180 }}, outlineLevel: 1 }}
      }}
    ]
  }},
  sections: [
    {{
      properties: {{
        page: {{
          size: {{ width: 12240, height: 15840 }},
          margin: {{ top: 1440, right: 1440, bottom: 1440, left: 1440 }}
        }}
      }},
      children
    }}
  ]
}});

Packer.toBuffer(doc).then(buffer => {{
  fs.writeFileSync(outputPath, buffer);
  console.log('DOCX OK: ' + outputPath);
}}).catch(error => {{
  console.error(error);
  process.exit(1);
}});
""".strip()

    with open(js_path, "w", encoding="utf-8") as handle:
        handle.write(script)

    env = os.environ.copy()
    try:
        npm_executable = shutil.which("npm") or shutil.which("npm.cmd") or "npm"
        npm_root = subprocess.run(
            [npm_executable, "root", "-g"],
            check=True,
            capture_output=True,
            text=True,
        ).stdout.strip()
        if npm_root:
            existing_node_path = env.get("NODE_PATH")
            env["NODE_PATH"] = (
                npm_root if not existing_node_path else os.pathsep.join([npm_root, existing_node_path])
            )
    except Exception as exc:
        print(f"[docx_generator] could not resolve global npm root: {exc}")

    try:
        proc = subprocess.run(
            ["node", js_path],
            env=env,
            capture_output=True,
            text=True,
            timeout=60,
        )
        if proc.stdout:
            print(f"[docx_generator] node stdout: {proc.stdout.strip()}")
        if proc.stderr:
            print(f"[docx_generator] node stderr: {proc.stderr.strip()}")
        if proc.returncode != 0:
            print(f"[docx_generator] node exited with code {proc.returncode} — docx skipped")
            return None
    except Exception as exc:
        print(f"[docx_generator] failed to run node script: {exc} — docx skipped")
        return None
    finally:
        try:
            os.remove(js_path)
        except OSError:
            pass

    return output_path
