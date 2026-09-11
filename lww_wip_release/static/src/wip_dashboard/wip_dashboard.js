/** @odoo-module **/

import { Component, onWillStart, useState } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";

export class WipDashboard extends Component {
    static template = "lww_wip_release.WipDashboard";
    static props = ["*"];

    setup() {
        this.orm = useService("orm");
        this.action = useService("action");
        this.state = useState({
            loading: true,
            kpi: { total: 0, eligible: 0, released: 0, unreleased: "" },
            projects: [],
            companies: [],
            companyId: false,
            search: "",
            status: false,
            offset: 0,
            limit: 10,
            count: 0,
        });
        onWillStart(() => this.load());
    }

    async load() {
        this.state.loading = true;
        const data = await this.orm.call(
            "project.project",
            "get_wip_dashboard_data",
            [],
            {
                company_id: this.state.companyId || false,
                search: this.state.search || "",
                status: this.state.status || false,
                offset: this.state.offset,
                limit: this.state.limit,
            }
        );
        this.state.kpi = data.kpi;
        this.state.projects = data.projects;
        this.state.companies = data.companies;
        this.state.count = data.count;
        this.state.loading = false;
    }

    get rangeLabel() {
        if (!this.state.count) {
            return "0 / 0";
        }
        const start = this.state.offset + 1;
        const end = Math.min(this.state.offset + this.state.limit, this.state.count);
        return `${start}-${end} / ${this.state.count}`;
    }

    onCompanyChange(ev) {
        this.state.companyId = ev.target.value ? parseInt(ev.target.value, 10) : false;
        this.state.offset = 0;
        this.load();
    }

    onSearchInput(ev) {
        this.state.search = ev.target.value;
        this.state.offset = 0;
        this.load();
    }

    toggleStatus(status) {
        this.state.status = this.state.status === status ? false : status;
        this.state.offset = 0;
        this.load();
    }

    previousPage() {
        if (this.state.offset === 0) {
            return;
        }
        this.state.offset = Math.max(0, this.state.offset - this.state.limit);
        this.load();
    }

    nextPage() {
        if (this.state.offset + this.state.limit >= this.state.count) {
            return;
        }
        this.state.offset += this.state.limit;
        this.load();
    }

    openProject(projectId) {
        this.action.doAction({
            type: "ir.actions.act_window",
            res_model: "project.project",
            res_id: projectId,
            views: [[false, "form"]],
            target: "current",
        });
    }

    runRelease() {
        this.action.doAction("lww_wip_release.action_wip_release_wizard", {
            onClose: () => this.load(),
        });
    }
}

registry.category("actions").add("lww_wip_release.dashboard", WipDashboard);
