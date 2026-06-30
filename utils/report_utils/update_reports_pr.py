#!/usr/bin/env python3
"""
utils/report_utils/update_reports_pr.py

Post-run script to dynamically update JSON, HTML, and Excel reports with
the actual GitHub Pull Request URL after the PR is successfully created.
"""

import argparse
import json
import os
import sys
import glob
from pathlib import Path

# Add root folder to sys.path to import conftest
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))
try:
    import conftest
except ImportError:
    conftest = None

def parse_args():
    parser = argparse.ArgumentParser(description="Update test reports with actual PR URL.")
    parser.add_argument("--pr-url", required=True, help="Actual GitHub PR URL.")
    parser.add_argument("--type", choices=["APP_HEAL", "TEST_HEAL", "MIXED"], default="APP_HEAL", help="Healing type.")
    parser.add_argument("--run-id", help="Pipeline Run ID.")
    return parser.parse_args()

def find_latest_report(directory, pattern):
    files = glob.glob(os.path.join(directory, pattern))
    if not files:
        return None
    # Sort by modification time desc
    files.sort(key=os.path.getmtime, reverse=True)
    return Path(files[0])

def update_json_and_html(run_id, pr_url):
    print(f"[*] Locating JSON/HTML reports for Run ID: {run_id or 'latest'}...")
    base_dir = Path(".")
    if not (base_dir / "reports").exists() and (base_dir.parent / "reports").exists():
        base_dir = base_dir.parent

    json_dir = base_dir / "reports/json"
    html_dir = base_dir / "reports/html"

    target_files = []
    if run_id:
        target_files.append((json_dir / f"test_results_{run_id}.json", html_dir / f"test_results_{run_id}.html"))
        target_files.append((json_dir / f"test_results_{run_id}_full_rerun.json", html_dir / f"test_results_{run_id}_full_rerun.html"))
    else:
        json_path = find_latest_report(str(json_dir), "test_results_*.json")
        if json_path:
            stem = json_path.stem
            clean_run_id = stem.replace("test_results_", "").replace("_full_rerun", "")
            target_files.append((json_dir / f"test_results_{clean_run_id}.json", html_dir / f"test_results_{clean_run_id}.html"))
            target_files.append((json_dir / f"test_results_{clean_run_id}_full_rerun.json", html_dir / f"test_results_{clean_run_id}_full_rerun.html"))

    existing_targets = [(jp, hp) for jp, hp in target_files if jp.exists()]

    if not existing_targets:
        print(f"[!] JSON report files not found. Skipping JSON/HTML update.")
        return False

    for json_path, html_path in existing_targets:
        print(f"[*] Patching JSON report: {json_path}")
        try:
            payload = json.loads(json_path.read_text(encoding="utf-8"))
        except Exception as e:
            print(f"[x] Error reading JSON: {e}")
            continue

        updated = False
        for result in payload.get("results", []):
            curr_pr = result.get("pr_url", "")
            status = result.get("status", "")
            is_healed = (status in ("PASS", "PASSED") and result.get("jira_id")) or "ai-fix" in str(curr_pr)
            if is_healed:
                result["pr_url"] = pr_url
                updated = True

        if updated:
            json_path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
            print(f"[+] JSON report updated successfully.")

            print(f"[*] Regenerating/patching HTML report: {html_path}")
            try:
                if conftest is not None:
                    html_content = conftest._build_html(payload, json_path.name)
                    html_path.write_text(html_content, encoding="utf-8")
                    print(f"[+] HTML report regenerated successfully using conftest.")
                else:
                    print(f"[*] conftest not imported (missing pytest). Attempting direct patch of existing HTML file...")
                    if html_path.exists():
                        content = html_path.read_text(encoding="utf-8")
                        import re
                        pattern = r'https://github\.com/softnauticsgithub/[a-zA-Z0-9_-]+/tree/ai-fix/[a-zA-Z0-9_-]+'
                        new_content = re.sub(pattern, pr_url, content)
                        html_path.write_text(new_content, encoding="utf-8")
                        print(f"[+] HTML report patched directly via regex replacement.")
                    else:
                        print(f"[!] HTML report does not exist. Cannot patch.")
            except Exception as e:
                print(f"[x] Error updating HTML report: {e}")
        else:
            print(f"[-] No healed/traceable test cases found in JSON report: {json_path.name}")

    return True

def update_excel_report(pr_url):
    base_dir = Path(".")
    if not (base_dir / "reports").exists() and (base_dir.parent / "reports").exists():
        base_dir = base_dir.parent

    excel_path = base_dir / "reports/test_results.xlsx"
    if not excel_path.exists():
        print(f"[!] Excel report not found at {excel_path}. Skipping Excel update.")
        return False

    print(f"[*] Locating and patching Excel report: {excel_path}")
    try:
        from openpyxl import load_workbook
        from openpyxl.styles import Font, PatternFill
    except ImportError:
        print("[x] openpyxl not installed. Cannot update Excel report.")
        return False

    try:
        wb = load_workbook(str(excel_path))
        if "Test Details" not in wb.sheetnames:
            print("[!] 'Test Details' sheet not found in Excel. Skipping Excel update.")
            return False

        ws = wb["Test Details"]
        headers = [ws.cell(row=1, column=col).value for col in range(1, ws.max_column + 1)]
        
        try:
            status_idx = headers.index("Status") + 1
        except ValueError:
            print("[x] 'Status' column not found in Excel sheet.")
            return False

        jira_id_idx = None
        if "Jira ID" in headers:
            jira_id_idx = headers.index("Jira ID") + 1

        pr_link_idx = None
        if "PR Link" in headers:
            pr_link_idx = headers.index("PR Link") + 1
        else:
            print("[!] 'PR Link' column not found in Excel sheet.")
            return False

        print(f"[*] 'Status' col index: {status_idx}, 'PR Link' col index: {pr_link_idx}")

        updated_count = 0
        for r in range(2, ws.max_row + 1):
            status = ws.cell(row=r, column=status_idx).value
            pr_cell = ws.cell(row=r, column=pr_link_idx)
            pr_val = pr_cell.value

            has_jira = False
            if jira_id_idx:
                jira_val = ws.cell(row=r, column=jira_id_idx).value
                if jira_val and str(jira_val).strip() not in ("", "N/A", "None"):
                    has_jira = True

            is_healed = (status == "PASSED" and has_jira) or (pr_val and "ai-fix" in str(pr_val))
            if is_healed:
                safe_url = str(pr_url).replace('"', '')
                pr_cell.value = f'=HYPERLINK("{safe_url}","Open PR")'
                pr_cell.font = Font(color="7C3AED", underline="single", bold=True)
                
                fill = PatternFill("solid", "E8DFFF")
                font = Font(color="4C1D95", bold=True)
                for c in range(1, ws.max_column + 1):
                    cell = ws.cell(row=r, column=c)
                    if c == pr_link_idx:
                        cell.fill = fill
                    elif jira_id_idx and c == jira_id_idx + 1:
                        cell.fill = fill
                    else:
                        cell.fill = fill
                        cell.font = font
                
                updated_count += 1

        if updated_count > 0:
            wb.save(str(excel_path))
            print(f"[+] Excel report updated successfully. Patched {updated_count} rows.")
        else:
            print(f"[-] No healed rows found in Excel sheet to update.")

    except Exception as e:
        print(f"[x] Error updating Excel report: {e}")
        return False

    return True

def main():
    args = parse_args()
    run_id = args.run_id or os.environ.get("REGRESSION_RUN_ID")
    
    success_json = update_json_and_html(run_id, args.pr_url)
    success_excel = update_excel_report(args.pr_url)
    
    if success_json or success_excel:
        print("[+] All reports updated successfully.")
    else:
        print("[-] Report update finished with no changes.")

if __name__ == "__main__":
    main()
