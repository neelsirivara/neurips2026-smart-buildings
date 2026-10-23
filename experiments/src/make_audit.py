"""Generate the claim -> artifact -> value table of paper/AUDIT.md from the same files the paper
macros come from, so the audit cannot drift from the PDF.

Reads paper/results_macros.tex (every \\newcommand) and emits one row per audited claim: the
claim as worded in the paper, the macro(s) carrying its number(s), the JSON file and key the
macro was computed from, and the current value(s). Rows whose value is still \\textbf{??} are
flagged. The hand-written header (build/conventions, directional checks) is kept in
paper/AUDIT_header.md and prepended.

Usage:  python make_audit.py
"""
from __future__ import annotations

import re
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
PAPER = ROOT / "paper"

# (claim in the paper, [macros], source)
CLAIMS = [
    ("Leaderboard metric, SADR v6 (final) vs pid_water run locally on one machine (abstract, Table 1)",
     ["MetricOurs", "MetricPidWater"], "results/final_scores.json -> policies.transfer.metric, policies.pid_water.metric"),
    ("Paired bootstrap ratio and CI vs pid_water; wins; Wilcoxon p (abstract, Sec. 4)",
     ["RatioPidWater", "RatioLoPidWater", "RatioHiPidWater", "WinsPidWater", "NScen", "PWilcoxonPidWater", "NBoot"],
     "final_scores.json -> comparisons.transfer_vs_pid_water"),
    ("Relative reduction vs pid_water with CI (Sec. 4)",
     ["RelRedPidWater", "RelRedLoPidWater", "RelRedHiPidWater"], "final_scores.json -> comparisons.transfer_vs_pid_water.ratio*"),
    ("v6 vs v4 in Table 1 (the Delta column of the v4 row)",
     ["MetricOursVFour", "DiffOursVFour", "DiffLoOursVFour", "DiffHiOursVFour"],
     "final_scores.json -> policies.transfer_v4, comparisons.transfer_vs_transfer_v4"),
    ("v4 -> v5 reduction with CI, wins and station differences (abstract, Sec. 4)",
     ["CandWinnerRelRed", "CandWinnerCiLo", "CandWinnerCiHi", "CandWinnerWins", "CandWinnerDiffPhoenix", "CandWinnerDiffSingapore", "CandWinnerDiffFairbanks"],
     "results/candidates_summary.json -> full.candidates[winner] (v5 vs v4 at full length on the Mac); station diffs = winner by_station - final_scores transfer_v4 by_station"),
    ("Round 3: v6 vs v5 on the public set (abstract, Table 1, Sec. 4)",
     ["MetricOursVFive", "DiffOursVFive", "DiffLoOursVFive", "DiffHiOursVFive", "RelRedOursVFive", "RelRedLoOursVFive", "RelRedHiOursVFive",
      "WinsOursVFive", "DiffOursVFiveFairbanks", "DiffOursVFivePhoenix", "PubVFiveRelRed"],
     "final_scores.json -> policies.transfer_v5, comparisons.transfer_vs_transfer_v5"),
    ("Round 3: v6 vs v5 and vs pid_water on the previous held-out set (Sec. 4)",
     ["HeldMetricOursVFive", "HeldRatioVFivePidWater", "HeldMetricOursVFiveBgenb", "HeldMetricOursVFiveBgena", "HeldRatio", "HeldRatioLo", "HeldRatioHi",
      "HeldVFiveDiff", "HeldVFiveDiffLo", "HeldVFiveDiffHi", "HeldVFiveWins"],
     "results/heldout_scores.json -> policies.transfer_v5, comparisons.transfer_vs_transfer_v5, transfer_vs_pid_water"),
    ("Round 3: the six new held-out buildings (abstract, Secs. 3-5)",
     ["NHeldR", "NHeldRBuild", "HeldRMetricOurs", "HeldRMetricOursVFive", "HeldRMetricPidWater", "HeldRVFiveDiff", "HeldRVFiveDiffLo", "HeldRVFiveDiffHi",
      "HeldRVFiveRatio", "HeldRVFiveRelRed", "HeldRVFiveWins", "HeldRVFivePWilcoxon", "HeldRPidWaterRatio", "HeldRPidWaterRatioLo", "HeldRPidWaterRatioHi",
      "HeldRPidWaterWins", "HeldRRatioVFivePidWater", "HeldRZonesMin", "HeldRZonesMax", "HeldRAhusMin", "HeldRAhusMax"],
     "results/heldout_r3_scores.json (score_all.py on results/final_heldout_r3: transfer = v6, transfer_v5, pid_water, all Mac runs)"),
    ("Round 3: both held-out sets pooled (40 scenarios, 8 buildings) and the subset never screened (abstract, Sec. 3, Sec. 4, Sec. 6)",
     ["NHeldAll", "NHeldAllBuild", "HeldAllMetricOurs", "HeldAllMetricOursVFive", "HeldAllMetricPidWater", "HeldAllVFiveDiff", "HeldAllVFiveDiffLo",
      "HeldAllVFiveDiffHi", "HeldAllVFiveRelRed", "HeldAllVFiveRelRedLo", "HeldAllVFiveRelRedHi", "HeldAllVFiveWins", "HeldAllVFivePWilcoxon",
      "HeldAllPidWaterRatio", "HeldAllPidWaterRatioLo", "HeldAllPidWaterRatioHi", "HeldAllPidWaterWins", "HeldAllRatioVFivePidWater",
      "NHeldUnscr", "HeldUnscrVFiveRelRed", "HeldUnscrVFiveRelRedLo", "HeldUnscrVFiveRelRedHi", "HeldUnscrVFiveWins", "NHeldScreened"],
     "make_macros.pooled_heldout_macros: per-scenario scores of heldout_scores.json + heldout_r3_scores.json, paired bootstrap as score_all.py (5,000 resamples, seed 0); unscreened = minus the six held-out scenarios of results/round3/screen_summary.json -> sets.held"),
    ("Round 3: candidates ledger -- verdicts against the v6 defaults, the shipped composite, c00 at full length (Sec. 4, Table B3)",
     ["NRThreeVariants", "NRThreeWorse", "NRThreeNs", "NRThreePubOnly", "NRThreeRuleMet", "ScreenCThreeHeldRatio", "ScreenCFourHeldRatio",
      "ScreenCElevenVerdict", "ScreenCTwelveVerdict", "ScreenCNineVerdict", "ScreenCSixVerdict", "ShippedCandId",
      "ScreenCSixteenPubDZero", "ScreenCSixteenPubDZeroLo", "ScreenCSixteenPubDZeroHi", "ScreenCSixteenHeldDZero", "ScreenCSixteenHeldDZeroLo",
      "ScreenCSixteenHeldDZeroHi", "FullCZeroPub", "FullShipVsCZeroPubDiff", "FullShipVsCZeroPubDiffLo", "FullShipVsCZeroPubDiffHi",
      "FullCZeroHeldN", "FullCZeroHeld", "FullCZeroHeldShip", "FullShipVsCZeroHeldDiffLo", "FullShipVsCZeroHeldDiffHi"],
     "results/round3/candidates.json (ledger_round3.py: candidates_notes.json + screen_summary.json + screen_summary_vs_r3_c00_v6_default.json + results/round3/laptop_full_c00_public + final_scores.json; c00 held-out: results/mac/round3/final_c00_{heldout,r3} vs final_v6_* and diag_v5_*)"),
    ("Round 3: v6 parameter values (Sec. 3, Table B0)",
     ["ParAreaRef", "ParAreaScaleMin", "ParAreaScaleMax", "ParFCapPre", "ParFCapOcc"],
     "results/tune/best_params.json == submission/best_params.json == DEFAULT_PARAMS of submission/transfer_policy.py (ship_round3.py + bake_params.py)"),
    ("Round 3: zone areas of the public, previous and new held-out buildings (Secs. 3-5)",
     ["PubZoneAreaMedian", "HeldRZoneAreaMin", "HeldRZoneAreaMedian", "HeldRZoneAreaMax", "ZoneAreaMedianBgena", "ZoneAreaMedianBgenb"],
     "zones.npz of the diag runs (zone_area_m2 from the metadata zone map, 4-connected rooms in raster order; identical to the simulator's room_dict on all 14 buildings, checked 2026-10-23)"),
    ("Round 3: loss decomposition by component, mode and ventilation share, v5 and v6 on the public set (Sec. 4, Fig. 2)",
     ["DecPubVFiveN", "DecPubVFiveGasShare", "DecPubVFiveCoolingShare", "DecPubVFiveFanShare", "DecPubVFivePumpShare", "DecPubVFiveComfortShare",
      "DecPubVFiveGasShareFairbanks", "DecPubVFiveCoolingShareSingapore", "DecPubVFiveModePreShare", "DecPubVFiveModeSbShare", "DecPubVFiveIdleMinflow",
      "DecPubOursGasShare", "DecPubOursCoolingShare", "DecPubOursComfortShare", "DecPubVFiveRecoveryBig"],
     "results/round3/loss_decomposition_public_v5.json, loss_decomposition_public_v6.json (decompose_loss.py on the run_diag.py outputs)"),
    ("Round 3: why v5 lost on large zones (Sec. 5)",
     ["DecHeldVFiveComfortShareBgenb", "DecHeldVFiveRecoveryBigBgenb", "TenDayVFiveScore", "TenDayVSixBScore", "TenDayVFiveRegret", "TenDayVSixBRegret",
      "TenDayVSixCScore", "DecHeldRVFiveRecoveryBig", "DecHeldROursRecoveryBig", "DecHeldRVFiveComfortShare", "DecHeldROursComfortShare"],
     "results/round3/loss_decomposition_heldout_v5.json, *_heldout_r3_v5.json, *_heldout_r3_v6.json; results/round3/b0502_{v5,v6b,v6c}/building_0502/denver_1/transfer/summary.json (2,880 steps, laptop)"),
    ("Round 3: screening of the v6 variants (Sec. 3, Sec. 4, Table B3)",
     ["NScreenCands", "ScreenSteps", "ScreenCZeroPubRatio", "ScreenCZeroPubWins", "ScreenCZeroHeldRatio", "ScreenCZeroHeldWins"],
     "results/round3/screen_summary.json (screen_round3.py; public screen on the laptop, held-out screen on the Mac)"),
    ("Per-station metrics (Table 1)",
     ["MetricOursFairbanks", "MetricOursDenver", "MetricOursAtlanta", "MetricOursPhoenix", "MetricOursSingapore",
      "MetricPidWaterFairbanks", "MetricPidWaterPhoenix"], "final_scores.json -> policies.*.by_station"),
    ("Station differences vs pid_water and vs v4 (Sec. 4)",
     ["DiffPidWaterFairbanks", "DiffPidWaterPhoenix", "DiffOursVFourPhoenix", "DiffOursVFourSingapore", "DiffOursVFourFairbanks"],
     "final_scores.json -> comparisons.*.by_station_diff"),
    ("Other organizer baselines, local runs and organizer values (Table 1)",
     ["MetricPid", "MetricFixedSp", "MetricBangBang", "MetricPidWaterOff", "RatioPidWaterOff"],
     "final_scores.json -> policies.pid/fixed_setpoint/bang_bang/pid_water_official; kit/baseline_returns.json"),
    ("Local-vs-official gap for pid_water (Sec. 4)",
     ["GapMeanPidWater", "GapMinPidWater", "GapMaxPidWater"], "final_scores.json -> local_vs_official_gap.pid_water"),
    ("Cross-machine check: v4 on the laptop vs the Mac (Sec. 4)",
     ["LocalVFourMetric", "MetricOursVFour", "MachineGapMean", "MachineGapMax", "MachineGapN"],
     "final_scores_local.json (laptop) vs final_scores.json -> policies.transfer_v4 per scenario"),
    ("Decomposition comfort/energy/carbon (Sec. 4, Fig. 2)",
     ["DecompOursComfort", "DecompOursEnergy", "DecompOursCarbon", "DecompPidWaterComfort", "DecompPidWaterEnergy", "DecompPidWaterCarbon"],
     "final_scores.json -> policies.*.decomp"),
    ("Held-out generated buildings (abstract, Sec. 4)",
     ["NHeld", "NHeldBuild", "HeldMetricOurs", "HeldMetricPidWater", "HeldMetricOursVFour", "HeldRatio", "HeldDiff", "HeldDiffLo", "HeldDiffHi", "HeldWins",
      "ZonesBgena", "AhusBgena", "ZonesBgenb", "AhusBgenb"], "results/heldout_scores.json"),
    ("Random search: counts and screening scores (Sec. 3, Sec. 4, Fig. C2)",
     ["NTuneConfigs", "NTuneRandom", "TuneDefaultScreen", "TuneBestScreen", "TuneWorstScreen", "TunePidWaterScreen"],
     "results/tune/tune_log.json (stage == random), results/tune_baseline/pid_water__agg.json"),
    ("Ablation: ki alone is the gain (Sec. 3, Table B1)",
     ["AblRelDefAddKi", "AblRelRevKi", "AblRelRevMarginPre", "AblRelRevSatMix", "AblRelRevSbHyst", "NAblation"],
     "results/tune/ablation.json (run on the Mac)"),
    ("v5 candidates on the screen and at full length (Sec. 4, Table B2)",
     ["NCandV", "CandBestScreen", "CandSatColdScreen", "CandNightEightScreen", "NCandFull", "CandWinner", "CandWinnerMetric",
      "CandWinnerVFourMetric", "CandWinnerRatio", "CandWinnerCiLo", "CandWinnerCiHi", "CandWinnerWins"],
     "results/candidates_summary.json (tune_log.json tag v5; results/mac/full_v5/*/transfer__agg.json vs results/mac/full/transfer__agg.json)"),
    ("Final parameter values (Table B0) and the v4 values v5 replaced (Sec. 3)",
     ["ParSatCoolHi", "ParNightLowExt", "ParNightHighExt", "ParMarginOcc", "ParKiWPerKStep", "VFourSatCoolHi", "VFourNightLowExt", "VFourNightHighExt", "ParSource"],
     "results/tune/best_params.json == submission/best_params.json == DEFAULT_PARAMS (bake_params.py); results/tune/ablation.json -> best.params (v4)"),
    ("Analysis shares: regret/energy/carbon/unoccupied, out-of-band zone-steps, hourly peak, first workday (Sec. 5)",
     ["NAnalysis", "RegretShareOurs", "EnergyShareOurs", "CarbonShareOurs", "UnoccShareOurs", "UnoccShareOursFairbanks", "OccOutOurs",
      "RegretSharePidWater", "OccOutPidWater", "OccWorstDevPidWater", "PeakLossHourOurs", "PeakLossShareOurs",
      "NFirstWorkdayWorse", "NFirstWorkdayTotal", "FirstWorkdayRatioMedianOurs"], "results/analysis.json (final tree, time series)"),
    ("Largest residual loss scenario; scenarios worse than pid_water (Sec. 5)",
     ["NScenWorse", "MaxOursScen", "MaxOursScore"], "final_scores.json -> per-scenario scores"),
    ("Organizer pid_water loses N x more in Fairbanks than in the mild climates (Sec. 2)",
     ["ExtremeRatioFairbanks"], "final_scores.json -> policies.pid_water_official.by_station"),
    ("v3 PI-held floor: handlers running during unoccupied steps (Sec. 3)",
     ["VthreeAhuOnUnocc"], "results/dev_full/building_train_8/fairbanks_8/transfer/{ahu_log.csv,timeseries.csv} (v3 snapshot)"),
    ("Extra boiler tank dissipation at 350 K vs 310 K (Sec. 3)", ["TankLossExtraKw"],
     "kit Boiler.compute_thermal_dissipation_rate(350,294) - (310,294), defaults of the kit"),
    ("Peak outside air in the Phoenix strips (Sec. 5)", ["PhoenixPeakOatC"], "results/final/*/phoenix_*/transfer*/ahu_log.csv or transfer/diag.csv -> max outside air"),
    ("Kaggle public leaderboard snapshot (Sec. 4)",
     ["LbDate", "LbNTeams", "LbRankOne", "LbRankEight", "LbRankThirty", "LbRankFortyNine", "OursVsLbOne"],
     "results/kaggle_leaderboard_2026-10-22.json (coordinator's read of the public leaderboard)"),
    ("Speed and compute (Sec. 3, Sec. 4, Sec. 7)",
     ["PolicyMsOurs", "SecPerStepOurs", "SimSecPerStep", "TotalCoreHours"],
     "final_scores.json -> policies.transfer.policy_ms_per_step_mean / seconds_per_step_mean; results/env_info.json"),
]


def main() -> int:
    macros = dict(re.findall(r"\\newcommand\{\\(\w+)\}\{(.*)\}\s*$", (PAPER / "results_macros.tex").read_text(encoding="utf-8"), re.M))
    header = (PAPER / "AUDIT_header.md").read_text(encoding="utf-8") if (PAPER / "AUDIT_header.md").exists() else "# AUDIT\n\n"
    L = [header.rstrip() + "\n\n## Claims -> artifacts -> values (generated by experiments/src/make_audit.py)\n\n",
         "| # | claim (paper location) | macro = value | artifact |\n|---|---|---|---|\n"]
    n_missing = 0
    for i, (claim, names, src) in enumerate(CLAIMS, 1):
        vals = []
        for n in names:
            v = macros.get(n, "(no macro)")
            if "??" in v or v == "(no macro)":
                n_missing += 1
                v = f"**{v}**"
            vals.append(f"`{n}`={v}")
        L.append(f"| {i} | {claim} | {'; '.join(vals)} | `{src}` |\n")
    L.append(f"\nMissing or placeholder values: {n_missing}\n")
    (PAPER / "AUDIT.md").write_text("".join(L), encoding="utf-8")
    print(f"wrote {PAPER / 'AUDIT.md'} ({len(CLAIMS)} claims, {n_missing} missing values)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
