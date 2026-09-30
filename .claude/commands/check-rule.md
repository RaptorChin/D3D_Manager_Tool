針對預檢規則 $ARGUMENTS（例如 E01）：
1. 在 `docs/SPEC_run_module.md` 找到規則定義，在 `docs/DOMAIN_NOTES_run_module.md` 找到背後原因。
2. 確認 `core/preflight.py` 的實作是否符合規格，並用 `tests/fixtures/` 組出「會觸發」與「不會觸發」兩個情境測試。
3. 回報差異並修正。
