def _backfill_partner(env, company_id=None, dry_run=True):
    domain = [('lww_entry_type', '!=', False), ('partner_id', '=', False)]
    if company_id:
        domain.append(('company_id', '=', company_id))
    moves = env['account.move'].sudo().search(domain, order='id')
    done, skipped, failed = [], [], []
    for move in moves:
        picking = move.lww_picking_id
        partner = (picking.sale_id.partner_id or picking.partner_id).commercial_partner_id
        if not partner:
            skipped.append((move.name, 'partner DO/SO tidak ditemukan'))
            continue
        if dry_run:
            done.append((move.name, partner.name))
            continue
        try:
            with env.cr.savepoint():
                move = move.with_context(skip_readonly_check=True)
                move.write({'partner_id': partner.id})
                move.line_ids.write({'partner_id': partner.id})
            done.append((move.name, partner.name))
        except Exception as e:
            failed.append((move.name, str(e).splitlines()[0][:120]))
    print('MODE:', 'DRY RUN (belum ada yang diubah)' if dry_run else 'DIUBAH (jangan lupa env.cr.commit())')
    print('Jurnal diproses :', len(done))
    print('Dilewati        :', len(skipped), skipped[:10])
    print('Gagal           :', len(failed), failed[:10])
    return done, skipped, failed
