def _refresh_all(env, dry_run=True, only_empty=False):
    Project = env['project.project'].sudo().with_context(active_test=False)
    Config = env['lww.recognition.config'].sudo()
    domain = [('lww_auto_year', '=', 0)] if only_empty else []
    stats = {}
    for company in env['res.company'].sudo().search([]):
        row = stats.setdefault(company.name, {'total': 0, 'diproses': 0, 'tahun_baru': 0, 'tanpa_so': 0, 'tanpa_config': 0, 'error': 0})
        projects = Project.search(domain + [('company_id', '=', company.id)], order='id')
        row['total'] = len(projects)
        if not Config._get(company):
            row['tanpa_config'] = len(projects)
            continue
        for project in projects.with_company(company):
            if not project._lww_sale_order():
                row['tanpa_so'] += 1
                continue
            before = project.lww_auto_year
            if dry_run:
                pct, date = project._lww_progress_data()
                row['diproses'] += 1
                if date and not before:
                    row['tahun_baru'] += 1
                continue
            try:
                with env.cr.savepoint():
                    project._lww_refresh_auto()
                    project.invalidate_recordset()
                row['diproses'] += 1
                if project.lww_auto_year and not before:
                    row['tahun_baru'] += 1
            except Exception as e:
                row['error'] += 1
                print('ERROR', project.id, project.name, str(e)[:120])
    print('MODE:', 'DRY RUN (belum ada yang diubah)' if dry_run else 'DIUBAH (jangan lupa env.cr.commit())')
    for name, row in stats.items():
        print(name, row)
    return stats
