def _regen_per_product(env, company_id=None, dry_run=True):
    from collections import Counter
    Move = env['account.move'].sudo()
    stats = Counter()
    problems = []
    domain = [('lww_active', '=', True), ('lww_entry_type', 'in', ('reclass', 'backdated')),
              ('lww_product_id', '=', False), ('state', '=', 'posted')]
    if company_id:
        domain.append(('company_id', '=', company_id))
    pickings = Move.search(domain).lww_picking_id.sorted('id')
    groups = (
        ('reclass', ('reclass', 'reversal_reclass'), 'reversal_reclass', 'Reversal Reclass', 'Reclass'),
        ('backdated', ('backdated', 'reversal_backdated'), 'reversal_backdated', 'Reversal Backdate', 'Backdate'),
    )
    for picking in pickings:
        picking = picking.with_company(picking.company_id)
        legacy = picking.x_move_ids.sudo().filtered(
            lambda m: m.lww_active and not m.lww_product_id and m.state == 'posted'
            and m.lww_entry_type in ('reclass', 'backdated'))
        year = picking.x_recognition_year or legacy[:1].lww_recognition_year
        if not year or not picking.x_do_date:
            stats['dilewati_tanpa_tahun'] += 1
            continue
        dates = [picking.x_do_date if t == 'reclass' else picking._lww_end_of_year(year)
                 for t in set(legacy.mapped('lww_entry_type'))]
        try:
            picking._lww_check_dates(picking.company_id, dates)
        except Exception as e:
            stats['gagal_lock_date'] += 1
            problems.append((picking.name, str(e)[:120]))
            continue
        if dry_run:
            stats['siap_dibuat_ulang'] += 1
            continue
        try:
            with env.cr.savepoint():
                net = picking._lww_net_lines()
                created = env['account.move']
                for etype, types, rev_type, rev_prefix, prefix in groups:
                    old = legacy.filtered(lambda m: m.lww_entry_type == etype)
                    if not old:
                        continue
                    move_date = picking.x_do_date if etype == 'reclass' else picking._lww_end_of_year(year)
                    ref_year = old[:1].lww_recognition_year or year
                    amounts = {k: -v for k, v in picking._lww_journal_net(types).items()}
                    created |= picking._lww_make_moves(rev_type, move_date, amounts, ref_year, rev_prefix)
                    old.write({'lww_active': False})
                    old.flush_recordset(['lww_active'])
                    target = {k: -v for k, v in net.items()} if etype == 'reclass' else dict(net)
                    created |= picking._lww_make_moves(etype, move_date, target, year, prefix)
                picking._lww_log('journal', picking.x_project_id, year, year, created,
                                 note='Regenerated per product')
            stats['dibuat_ulang'] += 1
        except Exception as e:
            stats['gagal'] += 1
            problems.append((picking.name, str(e)[:150]))
    print('MODE:', 'DRY RUN (belum ada yang diubah)' if dry_run else 'DIUBAH (jangan lupa env.cr.commit())')
    for key, val in stats.items():
        print('  %-24s %s' % (key, val))
    for row in problems[:30]:
        print('  GAGAL', row)
    return stats
