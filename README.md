# Prague IMAX 70mm — January 6–13, 2027

Checks Cinema City Flora's public Quickbook showtime feed on a **5-minute GitHub Actions schedule** using the newly created workflow [`imax70mm-five-minute.yml`](.github/workflows/imax70mm-five-minute.yml). Scheduled execution is best-effort and not guaranteed every 5 minutes.

- Watches **any film** at Cinema City Flora with both `IMAX` in the auditorium name and `70-mm` in the event attributes. Digital IMAX and ordinary 70mm are excluded.
- Only dates **January 6–13, 2027**, inclusive (Prague local time).
- New dates generate a GitHub Issue assigned to the repository owner, containing the date, film and a direct link to seat selection. The issue stays open to allow GitHub mobile push notifications to arrive (the GitHub Actions bot was confirmed to push successfully).
- Dedupe uses `state/seen.json`; no spam for previously seen events.
- Nothing to configure in the cinema's API; no secrets or payment data.
- Script stops querying after January 13, but the scheduled Actions workflow must be manually disabled.

## Activation required

1. Enable **Issues** under Settings → General → Features of this fork.
2. Open **Actions** tab and enable workflows if GitHub asks you to approve workflows for the fork.
3. Settings → Actions → General → **Workflow permissions**: grant read/write (and permissions to create issues if requested).
4. Open **Actions → Prague IMAX 70mm - five minute ticket watch → Run workflow**, verify the check succeeds.
5. Install GitHub on your phone and enable push notifications for assigned Issues. Configure GitHub notification preferences as needed.

## Important caveats

- GitHub scheduled workflows can be delayed or dropped. Five minutes is a target schedule, not a guaranteed reaction time.
- The Cinema City API uses the event attribute `70-mm`; it is coupled here with an IMAX auditorium name to avoid false positives.
- This app does not buy tickets; it provides purchase links. Please verify format at checkout.
- The repository and Issues may be public; never include payment/personal data.

## Verify the scheduler really runs

Open [the new workflow run history](https://github.com/Sigarya/cinemacity-watchdog/actions/workflows/imax70mm-five-minute.yml) and filter the event to `schedule`. These are the real automatic runs; `push` and `workflow_dispatch` are tests and do not prove that cron works. GitHub automatically disables scheduled workflows on forks and may delay/drop scheduled jobs.
