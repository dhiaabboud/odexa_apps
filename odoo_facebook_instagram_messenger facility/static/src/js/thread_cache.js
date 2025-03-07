/** @odoo-module **/

import { registerPatch } from "@mail/model/model_core";
import { attr, many, one } from '@mail/model/model_field';


registerPatch({
    name: 'ThreadCache',
    fields: {
        orderedNonEmptyMessages: {
            compute() {
                if(this.thread.isMessengerMsgs){
                    return this.orderedMessages.filter(message => !message.isEmpty && message.message_type=='facebook_msgs');
                }
                else if(this.thread.isInstagramMsgs){
                    return this.orderedMessages.filter(message => !message.isEmpty && message.message_type!='insta_msgs');
                }
            }

            },
        }
});