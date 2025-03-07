from odoo import _, api, fields, models, modules, tools, Command
import json
from collections import defaultdict
from odoo.tools.misc import DEFAULT_SERVER_DATETIME_FORMAT
from odoo.addons.mail.models.discuss.discuss_channel import Channel



def _channel_info(self):
    """ Get the information header for the current channels
        :returns a list of updated channels values
        :rtype : list(dict)
    """
    if not self:
        return []
    channel_infos = []
    # sudo: discuss.channel.rtc.session - reading sessions of accessible channel is acceptable
    rtc_sessions_by_channel = self.sudo().rtc_session_ids._mail_rtc_session_format_by_channel(extra=True)
    current_partner, current_guest = self.env["res.partner"]._get_current_persona()
    self.env['discuss.channel'].flush_model()
    self.env['discuss.channel.member'].flush_model()
    # Query instead of ORM for performance reasons: "LEFT JOIN" is more
    # efficient than "id IN" for the cross-table condition between channel
    # (for channel_type) and member (for other fields).
    self.env.cr.execute("""
             SELECT discuss_channel_member.id
               FROM discuss_channel_member
          LEFT JOIN discuss_channel
                 ON discuss_channel.id = discuss_channel_member.channel_id
                AND discuss_channel.channel_type != 'channel'
              WHERE discuss_channel_member.channel_id in %(channel_ids)s
                AND (
                    discuss_channel.id IS NOT NULL
                 OR discuss_channel_member.rtc_inviting_session_id IS NOT NULL
                 OR discuss_channel_member.partner_id = %(current_partner_id)s
                 OR discuss_channel_member.guest_id = %(current_guest_id)s
                )
           ORDER BY discuss_channel_member.id ASC
    """, {'channel_ids': tuple(self.ids), 'current_partner_id': current_partner.id or None, 'current_guest_id': current_guest.id or None})
    all_needed_members = self.env['discuss.channel.member'].browse([m['id'] for m in self.env.cr.dictfetchall()])
    all_needed_members._discuss_channel_member_format()  # prefetch in batch
    members_by_channel = defaultdict(lambda: self.env['discuss.channel.member'])
    invited_members_by_channel = defaultdict(lambda: self.env['discuss.channel.member'])
    member_of_current_user_by_channel = defaultdict(lambda: self.env['discuss.channel.member'])
    for member in all_needed_members:
        members_by_channel[member.channel_id] += member
        if member.rtc_inviting_session_id:
            invited_members_by_channel[member.channel_id] += member
        if (current_partner and member.partner_id == current_partner) or (current_guest and member.guest_id == current_guest):
            member_of_current_user_by_channel[member.channel_id] = member
    for channel in self:
        # Separate WhatsApp, Facebook and Instagram Channels
        custom_channel = ''
        if channel._fields.get('whatsapp_channel'):
            if channel.whatsapp_channel:
                custom_channel += 'WpChannels'
        if channel._fields.get('instagram_channel'):
            if channel.instagram_channel:
                custom_channel += 'InstaChannels'
        if channel._fields.get('facebook_channel'):
            if channel.facebook_channel:
                custom_channel += 'FbChannels'
        if not custom_channel:
            info = {
                'avatarCacheKey': channel._get_avatar_cache_key(),
                'channel_type': channel.channel_type,
                'memberCount': channel.member_count,
                'id': channel.id,
                'name': channel.name,
                'defaultDisplayMode': channel.default_display_mode,
                'description': channel.description,
                'uuid': channel.uuid,
                'state': 'open',
                'is_editable': channel.is_editable,
                'is_minimized': False,
                'group_based_subscription': bool(channel.group_ids),
                'create_uid': channel.create_uid.id,
                'authorizedGroupFullName': channel.group_public_id.full_name,
                'allow_public_upload': channel.allow_public_upload,
                'model': "discuss.channel",
            }
        else:
            info = {
                'avatarCacheKey': channel._get_avatar_cache_key(),
                'channel_type': custom_channel,
                'memberCount': channel.member_count,
                'id': channel.id,
                'name': channel.name,
                'defaultDisplayMode': channel.default_display_mode,
                'description': channel.description,
                'uuid': channel.uuid,
                'state': 'open',
                'is_editable': channel.is_editable,
                'is_minimized': False,
                'is_whatsapp': True,
                'group_based_subscription': bool(channel.group_ids),
                'create_uid': channel.create_uid.id,
                'authorizedGroupFullName': channel.group_public_id.full_name,
                'allow_public_upload': channel.allow_public_upload,
                'model': "discuss.channel",
            }
        # find the channel member state
        if current_partner or current_guest:
            info['message_needaction_counter'] = channel.message_needaction_counter
            member = member_of_current_user_by_channel.get(channel, self.env['discuss.channel.member']).with_prefetch([m.id for m in member_of_current_user_by_channel.values()])
            if member:
                info['channelMembers'] = [('ADD', list(member._discuss_channel_member_format().values()))]
                info['state'] = member.fold_state or 'open'
                info['message_unread_counter'] = member.message_unread_counter
                info['is_minimized'] = member.is_minimized
                info['custom_notifications'] = member.custom_notifications
                info['mute_until_dt'] = member.mute_until_dt.strftime(DEFAULT_SERVER_DATETIME_FORMAT) if member.mute_until_dt else False
                info['seen_message_id'] = member.seen_message_id.id
                info['custom_channel_name'] = member.custom_channel_name
                info['is_pinned'] = member.is_pinned
                info['last_interest_dt'] = member.last_interest_dt.strftime(DEFAULT_SERVER_DATETIME_FORMAT)
                if member.rtc_inviting_session_id:
                    info['rtc_inviting_session'] = {'id': member.rtc_inviting_session_id.id}
        # add members info
        if channel.channel_type != 'channel':
            # avoid sending potentially a lot of members for big channels
            # exclude chat and other small channels from this optimization because they are
            # assumed to be smaller and it's important to know the member list for them
            info['channelMembers'] = [('ADD', list(members_by_channel[channel]._discuss_channel_member_format().values()))]
            info['seen_partners_info'] = sorted([{
                'id': cm.id,
                'partner_id' if cm.partner_id else 'guest_id': cm.partner_id.id if cm.partner_id else cm.guest_id.id,
                'fetched_message_id': cm.fetched_message_id.id,
                'seen_message_id': cm.seen_message_id.id,
            } for cm in members_by_channel[channel]],
                key=lambda p: p.get('partner_id', p.get('guest_id')))
        # add RTC sessions info
        info.update({
            'invitedMembers': [('ADD', list(invited_members_by_channel[channel]._discuss_channel_member_format(
                fields={'id': True, 'channel': {}, 'persona': {'partner': {'id', 'name', 'im_status'}, 'guest': {'id', 'name', 'im_status'}}}).values()))],
            'rtcSessions': [('ADD', rtc_sessions_by_channel.get(channel, []))],
        })
        channel_infos.append(info)
    return channel_infos

Channel._channel_info = _channel_info


class MailChannel(models.Model):
    _inherit = "discuss.channel"

    instagram_channel = fields.Boolean(string="Instagram Channel")
    facebook_channel = fields.Boolean(string="Facebook Channel")


