import { CommonModule } from '@angular/common';
import { Component, OnInit, signal } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { errorMessage } from '../../core/error-message';
import { AuthService } from '../../core/auth.service';
import { OrganizationsService } from '../../core/api.services';
import { Invitation, Member, Role } from '../../core/models';

@Component({
  selector: 'app-users',
  standalone: true,
  imports: [CommonModule, FormsModule],
  template: `
    <div class="space-y-6">
      <div>
        <h1 class="text-xl font-semibold text-slate-900">Users &amp; roles</h1>
        <p class="text-sm text-slate-500">Manage who has access to this organization and what they can do.</p>
      </div>

      @if (error()) { <div class="notice" role="alert">{{ error() }}</div> }
      <div class="card p-5 overflow-x-auto">
        <h2 class="font-semibold text-slate-800 mb-3">Invite a member</h2>
        <form class="flex flex-wrap items-end gap-3" (ngSubmit)="invite()">
          <div>
            <label class="label" for="invite-email">Email</label>
            <input class="input" id="invite-email" name="email" type="email" required [(ngModel)]="inviteEmail" />
          </div>
          <div>
            <label class="label" for="invite-role">Role</label>
            <select class="input" id="invite-role" name="role" [(ngModel)]="inviteRole">
              <option value="viewer">Viewer</option>
              <option value="contributor">Contributor</option>
              <option value="content_owner">Content Owner</option>
              <option value="org_admin">Org Admin</option>
            </select>
          </div>
          <button class="btn-primary" type="submit" [disabled]="inviting()">{{ inviting() ? 'Creating…' : 'Create invitation' }}</button>
        </form>
        @if (inviteMessage()) {
          <p class="mt-2 text-sm text-emerald-700 break-all">{{ inviteMessage() }}</p>
        }
      </div>

      <div class="card p-5 overflow-x-auto">
        <h2 class="font-semibold text-slate-800 mb-3">Members</h2>
        <table class="w-full min-w-[650px] text-sm">
          <thead class="text-left text-xs uppercase text-slate-500 border-b border-slate-200">
            <tr>
              <th class="py-2">Name</th>
              <th class="py-2">Email</th>
              <th class="py-2">Role</th>
              <th class="py-2">Status</th>
              <th class="py-2"></th>
            </tr>
          </thead>
          <tbody class="divide-y divide-slate-100">
            @for (m of members(); track m.membership_id) {
              <tr>
                <td class="py-2">{{ m.full_name }}</td>
                <td class="py-2 text-slate-500">{{ m.email }}</td>
                <td class="py-2">
                  <select [attr.aria-label]="'Role for ' + m.full_name" [disabled]="busy() || !m.is_active || m.role === 'platform_admin'" class="input py-1 text-xs w-40" [ngModel]="m.role" (ngModelChange)="changeRole(m, $event)">
                    <option value="viewer">Viewer</option>
                    <option value="contributor">Contributor</option>
                    <option value="content_owner">Content Owner</option>
                    <option value="org_admin">Org Admin</option>
                  </select>
                </td>
                <td class="py-2">
                  <span class="badge" [ngClass]="m.is_active ? 'bg-emerald-50 text-emerald-700' : 'bg-slate-100 text-slate-500'">
                    {{ m.is_active ? 'Active' : 'Removed' }}
                  </span>
                </td>
                <td class="py-2 text-right">
                  @if (m.is_active) {
                    <button class="text-xs text-red-600 hover:text-red-700" [disabled]="busy()" (click)="removeMember(m)">Remove</button>
                  }
                </td>
              </tr>
            }
          </tbody>
        </table>
      </div>

      <div class="card p-5 overflow-x-auto">
        <h2 class="font-semibold text-slate-800 mb-3">Pending invitations</h2>
        @if (invitations().length === 0) {
          <p class="text-sm text-slate-500">No pending invitations.</p>
        } @else {
          <ul class="divide-y divide-slate-100 text-sm">
            @for (i of invitations(); track i.id) {
              <li class="py-2 flex items-center justify-between">
                <span>{{ i.email }} <span class="text-slate-400">({{ i.role }})</span></span>
                <div class="flex items-center gap-2">
                  <span class="badge bg-slate-100 text-slate-500">{{ i.status }}</span>
                  @if (i.status === 'pending') {
                    <button class="text-xs text-red-600 hover:text-red-700" [disabled]="busy()" (click)="revoke(i)">Revoke</button>
                  }
                </div>
              </li>
            }
          </ul>
        }
      </div>
    </div>
  `,
})
export class UsersComponent implements OnInit {
  members = signal<Member[]>([]);
  error = signal<string | null>(null); busy = signal(false);
  invitations = signal<Invitation[]>([]);
  inviteEmail = '';
  inviteRole: Role = 'viewer';
  inviting = signal(false);
  inviteMessage = signal<string | null>(null);

  constructor(public auth: AuthService, private orgService: OrganizationsService) {}

  async ngOnInit() {
    await this.reload();
  }

  async reload() {
    try {
      const [members, invitations] = await Promise.all([this.orgService.listMembers(), this.orgService.listInvitations()]);
      this.members.set(members); this.invitations.set(invitations);
    } catch (e) { this.error.set(errorMessage(e, 'People and invitations could not be loaded.')); }
  }
  private async action(work: () => Promise<unknown>) {
    if (this.busy()) return;
    this.busy.set(true); this.error.set(null);
    try { await work(); await this.reload(); }
    catch (e) { this.error.set(errorMessage(e, 'The change could not be saved.')); await this.reload(); }
    finally { this.busy.set(false); }
  }

  async invite() {
    if (this.inviting() || !this.inviteEmail.trim()) return;
    this.error.set(null); this.inviting.set(true);
    this.inviteMessage.set(null);
    try {
      const invitation = await this.orgService.invite(this.inviteEmail.trim(), this.inviteRole);
      const link = `${window.location.origin}/accept-invite?token=${invitation.token}`;
      this.inviteMessage.set(
        `Invitation created for ${this.inviteEmail}. Share this link with your teammate: ${link}`
      );
      this.inviteEmail = '';
      await this.reload();
    } catch (e) { this.error.set(errorMessage(e, 'The invitation could not be created.')); } finally {
      this.inviting.set(false);
    }
  }

  async changeRole(member: Member, role: string) {
    await this.action(async () => { await this.orgService.updateMemberRole(member.membership_id, role); if (member.user_id === this.auth.user()?.id) { await this.auth.loadCurrentUser(); window.location.assign('/dashboard'); } });
  }

  async removeMember(member: Member) {
    if (!window.confirm(`Remove ${member.full_name} from this workspace?`)) return;
    await this.action(() => this.orgService.removeMember(member.membership_id));
  }

  async revoke(invitation: Invitation) {
    await this.action(() => this.orgService.revokeInvitation(invitation.id));
  }
}
