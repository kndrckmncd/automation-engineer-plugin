---
name: client-profile-extractor
version: 1.0.0
description: >
  Extracts structured data from a GB Client Profile .doc file: Webpak Group #,
  Policyholder Name, Policy Outline table(s), and Booklet Outline table(s).
  Outputs a JSON object. Use when the user asks to extract, parse, or read a
  Client Profile document.
author: kndrckmncd
tools:
  - powershell
---

# Client Profile Extractor

## Purpose

Parse a GB Client Profile `.doc` file and extract the following into a JSON
object:

| Field | Source in document |
|---|---|
| `webpak_group_number` | "Webpak Group #" cell in the header table |
| `policyholder_name` | "Policyholder Name:" cell in the header table |
| `policy_outlines` | All "POLICY OUTLINE - XXXXX" tables |
| `booklet_outlines` | All "BOOKLET OUTLINE - XXXXX" tables |

Each Policy and Booklet Outline row captures the "Do not post to site approval
required" note (or any other inline comment) as a dedicated `"comment"` field.

## Prerequisites

- Microsoft Word installed (script uses `win32com` to open `.doc` files)
- `pywin32` installed: `pip install pywin32`

## Instructions

### Step 1 — Run the extraction script

```powershell
python skills\client-profile-extractor\scripts\extract-client-profile.py `
  --file "C:\path\to\ClientProfile.doc"
```

To also save the JSON to a file:

```powershell
python skills\client-profile-extractor\scripts\extract-client-profile.py `
  --file "C:\path\to\ClientProfile.doc" `
  --output "C:\Temp\client_profile.json"
```

### Step 2 — Review the output

The script prints JSON to stdout. Example output:

```json
{
  "webpak_group_number": "83143",
  "policyholder_name": "Bison Transport Inc.",
  "policy_outlines": [
    {
      "title": "POLICY OUTLINE - 83143",
      "rows": [
        {
          "policy_plan_doc_number": "31007",
          "comment": "",
          "epak_naming_convention": "policye1",
          "docunav_naming_convention": "",
          "cpmpdf_descriptions": "EAP, EAT, ELI, LTD, OEL, OSL",
          "sub_folders": "n/a"
        },
        {
          "policy_plan_doc_number": "83143",
          "comment": "Do not post to site approval required",
          "epak_naming_convention": "policye2",
          "docunav_naming_convention": "",
          "cpmpdf_descriptions": "DEN, EHC, STD",
          "sub_folders": "n/a"
        }
      ]
    }
  ],
  "booklet_outlines": [
    {
      "title": "BOOKLET OUTLINE - 83143",
      "rows": [
        {
          "pub_number": "31007100",
          "comment": "Do not post to site approval required",
          "class_numbers": "",
          "epak_naming_convention": "booksumea",
          "docunav_naming_convention": "",
          "cpmpdf_descriptions": "Executives",
          "sub_folders": "100"
        }
      ]
    }
  ]
}
```

## JSON Schema

### Top-level

| Key | Type | Description |
|---|---|---|
| `webpak_group_number` | string | Webpak/webpack group # from header |
| `policyholder_name` | string | Policyholder name from header |
| `policy_outlines` | array | One entry per "POLICY OUTLINE" table found |
| `booklet_outlines` | array | One entry per "BOOKLET OUTLINE" table found |

### Policy Outline row

| Key | Description |
|---|---|
| `policy_plan_doc_number` | Policy or plan document number |
| `comment` | Inline comment (e.g. "Do not post to site approval required") |
| `epak_naming_convention` | EPAK name (string or list if multiple) |
| `docunav_naming_convention` | Docunav name |
| `cpmpdf_descriptions` | CPM PDF description(s) (string or list if multiple) |
| `sub_folders` | Sub folder(s) / division numbers |

### Booklet Outline row

| Key | Description |
|---|---|
| `pub_number` | PUB # (provided by Doc IA) |
| `comment` | Inline comment (e.g. "Do not post to site approval required") |
| `class_numbers` | Class #'s / ManuConnect EHC Flex Codes |
| `epak_naming_convention` | EPAK name (string or list if multiple) |
| `docunav_naming_convention` | Docunav name |
| `cpmpdf_descriptions` | CPM PDF description(s) (string or list if bilingual) |
| `sub_folders` | Sub folder div numbers |

## Constraints

- Requires Microsoft Word to be installed — uses `win32com` to open `.doc` files
- Only `.doc` format is supported (not `.docx`)
- Tables are identified by the heading paragraph immediately preceding them;
  the script looks for "POLICY OUTLINE" and "BOOKLET OUTLINE" in the heading text
- Multi-value cells (e.g. bilingual EPAK names) are returned as a JSON array
- Cells with a single value are returned as a plain string (not an array)
