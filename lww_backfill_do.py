def _backfill_do(env, company_id=None, dry_run=True):
    from collections import Counter
    Picking = env['stock.picking'].sudo()
    Config = env['lww.recognition.config'].sudo()
    companies = env['res.company'].sudo().browse(company_id) if company_id else env['res.company'].sudo().search([])
    stats = Counter()
    problems = []
    for company in companies:
        config = Config._get(company)
        if not config:
            continue
        domain = [('company_id', '=', company.id), ('picking_type_code', '=', 'outgoing'), ('state', '=', 'done'),
                  ('return_id', '=', False), ('x_accounting_status', '=', False), ('date_done', '!=', False)]
        pickings = Picking.search(domain, order='date_done, id').with_company(company)
        for picking in pickings:
            do_date = picking.date_done.date()
            if do_date < config.go_live_date:
                stats['sebelum_go_live'] += 1
                continue
            project = picking._lww_find_project()
            if not project:
                stats['tanpa_project'] += 1
                continue
            year = project.lww_rec_year
            if not year:
                plan = 'awaiting'
            elif year < do_date.year:
                plan = 'jurnal_reklas_backdate'
            else:
                plan = 'recognized_tanpa_jurnal'
            if dry_run:
                stats[plan] += 1
                continue
            try:
                with env.cr.savepoint():
                    picking.write({'x_project_id': project.id, 'x_do_date': do_date})
                    for ret in picking.return_ids.filtered(lambda p: p.state == 'done' and p.date_done):
                        ret.write({'x_is_return': True, 'x_project_id': project.id, 'x_do_date': ret.date_done.date()})
                    if picking.return_ids.filtered(lambda p: p.state == 'done'):
                        picking.write({'x_has_return': True})
                    if not year:
                        picking.write({'x_accounting_status': 'awaiting'})
                        picking._lww_log('recognized', project, note='Awaiting recognition year (backfill)')
                    else:
                        if plan == 'jurnal_reklas_backdate':
                            picking._lww_require_config(config)
                            picking._lww_check_dates(company, [do_date, picking._lww_end_of_year(year)])
                        picking._lww_sync(year, project.lww_rec_mode, action='recognized')
                stats[plan] += 1
            except Exception as e:
                stats['gagal'] += 1
                problems.append((picking.name, str(e)[:150]))
    print('MODE:', 'DRY RUN (belum ada yang diubah)' if dry_run else 'DIUBAH (jangan lupa env.cr.commit())')
    for key, val in stats.items():
        print('  %-26s %s' % (key, val))
    for row in problems[:30]:
        print('  GAGAL', row)
    return stats
