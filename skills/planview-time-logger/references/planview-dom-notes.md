# Planview DOM Notes

## Timesheet Cell ID Pattern

```
{scheduleCode}###daily#{dayNumber}
```

**Day numbers:**
| Day  | Number |
|------|--------|
| Sun  | 1      |
| Mon  | 2      |
| Tue  | 3      |
| Wed  | 4      |
| Thu  | 5      |
| Fri  | 6      |
| Sat  | 7      |

**Example:** `207221###daily#4` = Wednesday cell for assignment with schedule code 207221

## Other Cell IDs

| ID Pattern              | Meaning                    |
|-------------------------|----------------------------|
| `{sc}###weekly`         | Weekly total cell          |
| `{sc}###total`          | Row total cell             |
| `{sc}###favorite`       | Pin-to-timesheet checkbox  |
| `{sc}###menu`           | Action menu button         |

## Key API Endpoints

| Endpoint                                    | Purpose              |
|---------------------------------------------|----------------------|
| `GET /planview/Track/Time/PickPeriod`        | List periods         |
| `GET /planview/Track/Time/Report`            | View/edit timesheet  |
| `GET /planview/Track/Time/SelectWork`        | Add work items       |
| `POST /planview/Track/Time/UpdateReport`     | Save hours (AJAX)    |
| `POST /planview/Track/Time/SignReport`       | Sign timesheet       |

## URL Parameters

- `resourceCode=128447` — Sean's resource code (fixed)
- `periodNumber=738` — period number (changes per period; extracted from PickPeriod links)

## Jira GL Code Field

- Field: `customfield_25042` → "Related GL Code"
- Found on Epic issue type
- Value example: `EC10010145`
- Matches Planview project name: `Ops GB Enhancements • EC10010145`

## Known GL Code Mappings (Sean's Projects)

| GL Code     | Planview Project                        | Jira Epic Example  |
|-------------|------------------------------------------|--------------------|
| EC10010145  | Ops GB Enhancements • EC10010145        | CTFSLBEB-619       |
| EC10010143  | Ops Bank Enhancements • EC10010143      | —                  |
| EC10010144  | Ops DMS Enhancements • EC10010144       | —                  |
| SC10009966  | Asset Sustainment (CTF) • SC10009966    | —                  |
| SC10010065  | GitHub Wave/EMU • SC10010065            | —                  |
| PC10010071  | Ops Automation • PC10010071             | —                  |

## Cell Interaction Pattern

1. Find `<td id="{sc}###daily#{dn}">` element
2. Click it → Planview JS activates an inline `<input>` inside the cell
3. Clear and type the hours value (e.g., `7.5`)
4. Send Tab key to commit and move to next cell
5. Page auto-saves via AJAX to `UpdateReport`

## Select Work Page

- URL: `/planview/Track/Time/SelectWork?resourceCode=128447&periodNumber={pn}`
- Filter panel: radio buttons for "Assigned This Period" / "All Periods"
- Assignment type checkboxes: Allocations, Authorizations, Tickets
- Assignment list: grouped by project heading (h4/h5 with GL code)
- Each assignment has a checkbox — check to add to timesheet
- Click "Done" link to return to Report page
