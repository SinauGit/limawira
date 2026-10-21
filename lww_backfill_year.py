def _backfill_year(env, company_id=None, dry_run=True):
    domain = [('lww_auto_year', '=', 0)]
    if company_id:
        domain.append(('company_id', '=', company_id))
    projects = env['project.project'].sudo().with_context(active_test=False).search(domain, order='id')
    ready, no_so, no_config, below = [], [], [], 0
    for project in projects:
        if not project._lww_sale_order():
            no_so.append(project.name)
            continue
        if not env['lww.recognition.config']._get(project.company_id):
            no_config.append(project.name)
            continue
        pct, date = project._lww_progress_data()
        if not date:
            below += 1
            continue
        ready.append((project.name, round(pct, 2), date))
        if not dry_run:
            project._lww_refresh_auto()
    print('MODE:', 'DRY RUN (belum ada yang diubah)' if dry_run else 'DIUBAH (jangan lupa env.cr.commit())')
    print('Project tanpa tahun   :', len(projects))
    print('Siap diisi tahunnya   :', len(ready))
    for row in ready[:30]:
        print('   ', row)
    print('Belum mencapai thresh.:', below)
    print('Tanpa SO              :', len(no_so), no_so[:10])
    print('Config belum ada      :', len(no_config), no_config[:10])
    return ready
