from __future__ import annotations

import threading
from queue import Queue, Empty
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any

from nicegui import ui
import logging

# Reuse existing app components (align with src/main.py path handling)
import os
import sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from . import main as core  # type: ignore  # gives access to config, db, scraper, enricher, exporter, hubspot, proxy_manager, rate_limiter
from .main import initialize_components  # type: ignore


_ui_log_handler_added = False


def init_core() -> None:
    ok = initialize_components()
    if not ok:
        raise RuntimeError('Failed to initialize core components')
    # Attach a UI log handler to forward all logs to the in-app log panel
    global _ui_log_handler_added
    if not _ui_log_handler_added:
        class UILogHandler(logging.Handler):  # local class to avoid import cycles
            def __init__(self, level=logging.INFO):
                super().__init__(level=level)
                fmt = logging.Formatter('%(asctime)s | %(name)s | %(levelname)s | %(message)s', datefmt='%H:%M:%S')
                self.setFormatter(fmt)
            def emit(self, record: logging.LogRecord) -> None:  # pragma: no cover
                try:
                    msg = self.format(record)
                    log.q.put(msg)
                except Exception:
                    pass

        root_logger = logging.getLogger()
        handler = UILogHandler(level=root_logger.level)
        root_logger.addHandler(handler)
        _ui_log_handler_added = True


class UILogger:
    def __init__(self) -> None:
        self.q: Queue[str] = Queue()
        self.lines: List[str] = []
        self.max_lines = 300

    def log(self, message: str) -> None:
        timestamp = datetime.now().strftime('%H:%M:%S')
        self.q.put(f'[{timestamp}] {message}')

    def drain(self) -> List[str]:
        updated = False
        while True:
            try:
                line = self.q.get_nowait()
                self.lines.append(line)
                updated = True
            except Empty:
                break
        if len(self.lines) > self.max_lines:
            self.lines = self.lines[-self.max_lines :]
        return self.lines if updated else []


log = UILogger()


def run_search(
    query: str,
    location: Optional[str],
    max_results: int,
    enrich: bool,
    export: str,
    filename: Optional[str],
) -> Dict[str, Any]:
    logger = log

    # Rate limit check
    limits_check = core.rate_limiter.check_limits('scrapingdog')
    if not limits_check['can_proceed']:
        return {
            'success': False,
            'error': 'Rate limits exceeded',
            'limits': limits_check,
        }

    # Estimate cost
    est_cost = core.scraper.estimate_cost(max_results)
    logger.log(f"Searching '{query}' in '{location or 'global'}' | max={max_results} | est=${est_cost:.4f}")

    job_id = core.generate_job_id(query, location)
    core.db.create_search_job(
        job_id, query, location, {
            'max_results': max_results,
            'enrich': enrich,
            'export_format': export,
        },
    )

    # Perform search
    logger.log('Contacting Google Maps via ScrapingDog...')
    results = core.scraper.search(query, location, max_results)
    if not results:
        core.db.update_search_job(job_id, status='completed', total_results=0, processed_results=0)
        return {'success': True, 'results': [], 'export_path': None, 'job_id': job_id}

    actual_pages = min((len(results) + 19) // 20, 6)
    actual_cost = actual_pages * core.scraper.get_cost_per_request()
    core.db.log_api_call('scrapingdog', 'google_maps_search', actual_cost, success=True)

    processed_businesses: List[Dict[str, Any]] = []
    for result in results:
        business_data = core.format_business_data(result, job_id)
        core.db.insert_business(business_data)
        processed_businesses.append(business_data)

    core.db.update_search_job(
        job_id,
        status='scraped',
        total_results=len(results),
        processed_results=len(processed_businesses),
    )
    logger.log(f'Found {len(processed_businesses)} businesses')

    # Enrichment
    if enrich:
        logger.log('Enriching with email addresses...')
        enriched_count = 0
        for business in processed_businesses:
            try:
                enriched = core.enricher.enrich_business(business)
                if enriched.get('email'):
                    enriched_count += 1
                core.db.insert_business(enriched)
                business.update(enriched)
            except Exception as e:  # pragma: no cover
                logger.log(f"Enrichment error for {business.get('name')}: {e}")
        core.db.update_search_job(job_id, status='enriched')
        logger.log(f'Enriched {enriched_count}/{len(processed_businesses)}')

    # Export
    export_path = None
    if export in ['csv', 'json']:
        export_path = core.exporter.export_businesses(
            processed_businesses,
            format_type=export,
            filename=filename,
            job_id=job_id,
        )
        logger.log(f'Exported to {export_path}')
    elif export == 'hubspot':
        if not core.hubspot.enabled:
            logger.log('HubSpot not enabled; skipping upload')
        else:
            contacts = core.exporter.create_hubspot_format(processed_businesses)
            if contacts:
                res = core.hubspot.upload_contacts(contacts)
                if res.get('success'):
                    logger.log(f"Uploaded {res.get('uploaded', 0)} contacts to HubSpot")
                else:
                    logger.log(f"HubSpot upload failed: {res.get('error')}")

    core.db.update_search_job(job_id, status='completed')
    logger.log(f'Job {job_id} completed')
    return {'success': True, 'results': processed_businesses, 'export_path': export_path, 'job_id': job_id}


def run_costs(current_month: bool, days: int, export_report: bool) -> Dict[str, Any]:
    if current_month:
        now = datetime.now()
        days = now.day
    summary = core.db.get_cost_summary(days)
    report_path = None
    if export_report:
        report_path = core.exporter.export_cost_report(days)
    return {'summary': summary, 'days': days, 'report_path': report_path}


def page_header() -> None:
    with ui.header().classes('items-center justify-between'):
        ui.label('Google Maps Lead Generator').classes('text-xl font-semibold')
        with ui.row().classes('gap-4'):
            ui.link('Status', '#status')
            ui.link('Search', '#search')
            ui.link('Batch', '#batch')
            ui.link('Costs', '#costs')


def page_status() -> None:
    ui.separator()
    ui.label('Status').props('id=status').classes('text-lg font-medium mt-4')
    with ui.card().classes('w-full'):
        cfg = core.config
        ui.label('Configuration')
        ui.markdown(
            f"- ScrapingDog: {'Configured' if cfg.get('apis.scrapingdog.api_key') not in (None, '', 'YOUR_SCRAPINGDOG_API_KEY_HERE') else 'Not configured'}\n"
            f"- Hunter.io: {'Enabled' if cfg.get('apis.hunter.enabled') else 'Disabled'}\n"
            f"- HubSpot: {'Enabled' if cfg.get('hubspot.enabled') else 'Disabled'}\n"
        )
        ui.label('Rate Limits')
        ui.markdown(
            f"- Daily: {cfg.get('settings.daily_limit', 10000):,}\n"
            f"- Weekly: {cfg.get('settings.weekly_limit', 50000):,}\n"
            f"- Monthly: {cfg.get('settings.monthly_limit', 200000):,}\n"
        )
        try:
            businesses = core.db.get_businesses_for_export(limit=None)
            enriched_count = len([b for b in businesses if b.get('email')])
            ui.label('Database')
            ui.markdown(f"- Total businesses: {len(businesses)}\n- With email addresses: {enriched_count}")
        except Exception as e:
            ui.markdown(f"Database error: {e}")


def page_search() -> None:
    ui.separator()
    ui.label('Search').props('id=search').classes('text-lg font-medium mt-4')

    query_in = ui.input('Query').classes('w-full').props('clearable')
    loc_in = ui.input('Location (optional)').classes('w-full').props('clearable')
    max_in = ui.number('Max results', value=100, min=1, max=200)
    enrich_sw = ui.switch('Enrich with emails', value=True)
    export_sel = ui.select(['csv', 'json', 'hubspot'], value='csv', label='Export format')
    fname_in = ui.input('Custom filename (optional, no extension)').props('clearable')

    output = ui.markdown('').classes('w-full h-56 overflow-auto border rounded p-2 bg-gray-50')

    def poll_logs() -> None:
        lines = log.drain()
        if lines:
            output.set_content('\n'.join(lines))

    ui.timer(0.5, poll_logs)

    def start_search() -> None:
        if not query_in.value:
            ui.notify('Please provide a query', color='negative')
            return

        client = ui.get_client()

        def worker() -> None:
            res = run_search(
                query=query_in.value,
                location=(loc_in.value or None),
                max_results=int(max_in.value or 100),
                enrich=bool(enrich_sw.value),
                export=str(export_sel.value),
                filename=(fname_in.value or None),
            )
            if res.get('success'):
                if res.get('export_path'):
                    log.log(f"Done. Export: {res['export_path']}")
                # Enter UI context from background thread for notifications
                with client:
                    ui.notify('Search completed', color='positive')
            else:
                with client:
                    ui.notify(f"Search failed: {res.get('error')}", color='negative')

        threading.Thread(target=worker, daemon=True).start()

    with ui.row().classes('mt-2 gap-2'):
        ui.button('Run Search', on_click=start_search)
        ui.button('Clear Logs', on_click=lambda: (log.lines.clear(), output.set_content('')))


def page_batch() -> None:
    ui.separator()
    ui.label('Batch').props('id=batch').classes('text-lg font-medium mt-4')

    path_in = ui.input('CSV path (query,location,max_results)').classes('w-full')
    enrich_sw = ui.switch('Enrich with emails', value=True)
    export_sel = ui.select(['csv', 'json', 'hubspot'], value='csv', label='Export format')

    output = ui.markdown('').classes('w-full h-56 overflow-auto border rounded p-2 bg-gray-50')

    def poll_logs() -> None:
        lines = log.drain()
        if lines:
            output.set_content('\n'.join(lines))

    ui.timer(0.5, poll_logs)

    def start_batch() -> None:
        import csv
        p = (path_in.value or '').strip()
        if not p:
            ui.notify('Please provide a CSV path', color='negative')
            return

        client = ui.get_client()

        def worker() -> None:
            try:
                searches: List[Dict[str, Any]] = []
                with open(p, 'r', encoding='utf-8') as f:
                    reader = csv.DictReader(f)
                    for row in reader:
                        if 'query' in row:
                            searches.append({
                                'query': row['query'],
                                'location': row.get('location') or None,
                                'max_results': int(row.get('max_results', 100) or 100),
                            })
                if not searches:
                    ui.notify('No valid searches found', color='warning')
                    return
                total = 0
                for i, s in enumerate(searches, 1):
                    log.log(f"Batch {i}/{len(searches)}: {s['query']} | {s.get('location') or 'global'}")
                    res = run_search(
                        query=s['query'],
                        location=s.get('location'),
                        max_results=s['max_results'],
                        enrich=bool(enrich_sw.value),
                        export=str(export_sel.value),
                        filename=None,
                    )
                    if res.get('success'):
                        total += len(res.get('results') or [])
                log.log(f'Batch completed. Total businesses processed: {total}')
                with client:
                    ui.notify('Batch completed', color='positive')
            except Exception as e:  # pragma: no cover
                log.log(f'Batch failed: {e}')
                with client:
                    ui.notify(f'Batch failed: {e}', color='negative')

        threading.Thread(target=worker, daemon=True).start()

    with ui.row().classes('mt-2 gap-2'):
        ui.button('Run Batch', on_click=start_batch)
        ui.button('Clear Logs', on_click=lambda: (log.lines.clear(), output.set_content('')))


def page_costs() -> None:
    ui.separator()
    ui.label('Costs').props('id=costs').classes('text-lg font-medium mt-4')

    current_month = ui.switch('Current month only', value=False)
    days = ui.number('Days (ignored if current month)', value=30, min=1, max=365)
    export_report = ui.switch('Export detailed report (CSV)', value=False)
    result = ui.markdown('')

    def run() -> None:
        res = run_costs(bool(current_month.value), int(days.value or 30), bool(export_report.value))
        summary = res.get('summary') or {}
        total_cost = (summary.get('summary') or {}).get('total_cost', 0)
        total_calls = (summary.get('summary') or {}).get('total_calls', 0)
        rp = res.get('report_path')
        md = [
            f"- Period: last {res.get('days')} days",
            f"- Total cost: ${total_cost:.4f}",
            f"- Total API calls: {total_calls}",
        ]
        if rp:
            md.append(f"- Report: {rp}")
        result.set_content('\n'.join(md))
        ui.notify('Cost analysis updated', color='positive')

    ui.button('Analyze Costs', on_click=run).classes('mt-2')


def create_app() -> None:
    init_core()
    page_header()
    with ui.column().classes('w-full q-ma-md'):
        page_status()
        page_search()
        page_batch()
        page_costs()


if __name__ in {'__main__', '__mp_main__'}:
    create_app()
    ui.run(title='GMaps Lead Generator', reload=False)
