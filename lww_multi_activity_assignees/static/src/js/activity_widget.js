/** @odoo-module **/

import { patch } from "@web/core/utils/patch";
import { ActivityModel } from "@mail/core/web/activity_model";
import { Activity } from "@mail/core/web/activity";

// Patch Activity Model untuk support multi-assignee
patch(ActivityModel.prototype, {
    setup() {
        super.setup();
        // Add computed field untuk all assigned users
        this.allAssignedUsers = [];
    },
    
    async load() {
        await super.load();
        // Load related activities untuk mendapatkan semua assigned users
        if (this.id) {
            const relatedActivities = await this.env.services.orm.searchRead(
                "mail.activity",
                [
                    ["res_model", "=", this.res_model],
                    ["res_id", "=", this.res_id],
                    ["activity_type_id", "=", this.activity_type_id.id],
                    ["date_deadline", "=", this.date_deadline],
                    ["summary", "=", this.summary || false],
                ],
                ["user_id"],
                { limit: 50 }
            );
            
            this.allAssignedUsers = relatedActivities.map(act => ({
                id: act.user_id[0],
                name: act.user_id[1],
            }));
        }
    },
});

// Patch Activity Component untuk display multi-assignee
patch(Activity.prototype, {
    setup() {
        super.setup();
    },
    
    get hasMultipleAssignees() {
        return this.activity.allAssignedUsers && this.activity.allAssignedUsers.length > 1;
    },
    
    get assignedUsersDisplay() {
        if (!this.hasMultipleAssignees) {
            return "";
        }
        
        const users = this.activity.allAssignedUsers;
        const displayUsers = users.slice(0, 3).map(u => u.name);
        let text = displayUsers.join(", ");
        
        if (users.length > 3) {
            text += ` ... (+${users.length - 3} more)`;
        }
        
        return text;
    },
});