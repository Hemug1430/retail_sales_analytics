import glob, os, subprocess, sys, time
def run():
    print("="*82); print("STEP 09.46: MASTER END-TO-END REGRESSION TEST SUITE (PHASE 09 QA)"); print("="*82)
    scripts = sorted([p for p in glob.glob("src/09.*.py") if not os.path.basename(p).startswith("09.46")])
    print(f"Discovered {len(scripts)} QA Regression Modules to Execute:\n")
    passed_suites, failed_suites = 0, 0
    t_all = time.perf_counter()
    for idx, script in enumerate(scripts, 1):
        t0 = time.perf_counter()
        res = subprocess.run([sys.executable, script], capture_output=True, text=True)
        dt = time.perf_counter() - t0
        out = (res.stdout or "") + "\n" + (res.stderr or "")
        has_zero_fail = ("Failed Checks: 0" in out) or ("Failed: 0" in out) or ("\nOK" in out)
        no_fail_tag = "[FAIL]" not in out
        ok = (res.returncode == 0) and has_zero_fail and no_fail_tag
        status = "PASS" if ok else "FAIL"
        print(f"  [{idx:02d}/{len(scripts):02d}] {os.path.basename(script):<44} | {status:<4} | {dt:>5.2f}s")
        if ok: passed_suites += 1
        else:
            failed_suites += 1
            for line in out.splitlines():
                if "[FAIL]" in line or "Error" in line or "SUMMARY" in line: print(f"       -> {line.strip()}")
    tot_s = time.perf_counter() - t_all
    print("\n" + "="*82)
    print(f"REGRESSION SUMMARY -> Total Suites: {len(scripts)} | Passed: {passed_suites} | Failed: {failed_suites} | Time: {tot_s:.2f}s")
    print("="*82)
if __name__=="__main__": run()


