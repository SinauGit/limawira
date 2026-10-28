def _delete_legacy(env, company_id=None, dry_run=True):
    from collections import Counter, defaultdict
    from odoo.tools import float_is_zero
    Move = env['account.move'].sudo()
    types = ('reclass', 'backdated', 'reversal_reclass', 'reversal_backdated')
    groups = (('reclass', 'reversal_reclass'), ('backdated', 'reversal_backdated'))
    domain = [('lww_entry_type', 'in', types), ('lww_product_id', '=', False), ('lww_picking_id', '!=', False)]
    if company_id:
        domain.append(('company_id', '=', company_id))
    stats = Counter()
    problems = []
    for picking in Move.search(domain).lww_picking_id.sorted('id'):
        company = picking.company_id
        old = picking.x_move_ids.sudo().filtered(lambda m: not m.lww_product_id and m.lww_entry_type in types)
        if old.filtered(lambda m: m.lww_active):
            stats['dilewati_belum_diregenerasi'] += 1
            continue
        safe = True
        for group in groups:
            net = defaultdict(float)
            for move in old.filtered(lambda m: m.state == 'posted' and m.lww_entry_type in group):
                for line in move.line_ids:
                    net[(line.account_id.id, tuple(sorted((line.analytic_distribution or {}).items())))] += \
                        line.debit - line.credit
            if any(not float_is_zero(v, precision_digits=2) for v in net.values()):
                safe = False
        if not safe:
            stats['dilewati_tidak_netral'] += 1
            problems.append((picking.name, 'jurnal lama dan reversalnya tidak saling meniadakan'))
            continue
        if company.check_account_audit_trail:
            stats['dilewati_audit_trail_aktif'] += 1
            continue
        try:
            picking._lww_check_dates(company, old.mapped('date'))
        except Exception as e:
            stats['gagal_lock_date'] += 1
            problems.append((picking.name, str(e)[:120]))
            continue
        if dry_run:
            stats['siap_dihapus'] += 1
            stats['jurnal_akan_dihapus'] += len(old)
            continue
        try:
            with env.cr.savepoint():
                count = len(old)
                posted = old.filtered(lambda m: m.state == 'posted')
                posted.button_draft()
                old.with_context(force_delete=True).unlink()
                picking._lww_log('journal', picking.x_project_id, picking.x_recognition_year,
                                 picking.x_recognition_year, note='Legacy journals deleted (%s)' % count)
            stats['dihapus'] += 1
            stats['jurnal_dihapus'] += count
        except Exception as e:
            stats['gagal'] += 1
            problems.append((picking.name, str(e)[:150]))
    print('MODE:', 'DRY RUN (belum ada yang diubah)' if dry_run else 'DIUBAH (jangan lupa env.cr.commit())')
    for key, val in stats.items():
        print('  %-30s %s' % (key, val))
    for row in problems[:30]:
        print('  GAGAL', row)
    return stats
