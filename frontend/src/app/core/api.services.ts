import { HttpClient } from '@angular/common/http';
import { Injectable } from '@angular/core';
import { firstValueFrom } from 'rxjs';
import { environment } from '../../environments/environment';
import {
  Application,
  ApplicationModule,
  AskResponse,
  AuditLogEntry,
  FeedbackEntry,
  Invitation,
  Member,
  Organization,
  SourceDetail,
  SourceSummary,
  TranscriptChunk,
  UsageSummary,
} from './models';

const base = environment.apiBaseUrl;

@Injectable({ providedIn: 'root' })
export class OrganizationsService {
  constructor(private http: HttpClient) {}

  getCurrent() {
    return firstValueFrom(this.http.get<Organization>(`${base}/organizations/current`));
  }
  update(payload: Partial<Pick<Organization, 'name' | 'logo_url' | 'retention_days'>>) {
    return firstValueFrom(this.http.patch<Organization>(`${base}/organizations/current`, payload));
  }
  listMembers() {
    return firstValueFrom(this.http.get<Member[]>(`${base}/organizations/current/members`));
  }
  updateMemberRole(membershipId: string, role: string) {
    return firstValueFrom(
      this.http.patch<Member>(`${base}/organizations/current/members/${membershipId}/role`, { role })
    );
  }
  removeMember(membershipId: string) {
    return firstValueFrom(this.http.delete(`${base}/organizations/current/members/${membershipId}`));
  }
  listInvitations() {
    return firstValueFrom(this.http.get<Invitation[]>(`${base}/organizations/current/invitations`));
  }
  invite(email: string, role: string) {
    return firstValueFrom(
      this.http.post<Invitation>(`${base}/organizations/current/invitations`, { email, role })
    );
  }
  revokeInvitation(id: string) {
    return firstValueFrom(this.http.post(`${base}/organizations/current/invitations/${id}/revoke`, {}));
  }
  acceptInvitation(token: string) {
    return firstValueFrom(this.http.post<Member>(`${base}/organizations/invitations/accept`, { token }));
  }
}

@Injectable({ providedIn: 'root' })
export class ApplicationsService {
  constructor(private http: HttpClient) {}

  list() {
    return firstValueFrom(this.http.get<Application[]>(`${base}/applications`));
  }
  get(id: string) {
    return firstValueFrom(this.http.get<Application>(`${base}/applications/${id}`));
  }
  create(payload: Partial<Application>) {
    return firstValueFrom(this.http.post<Application>(`${base}/applications`, payload));
  }
  update(id: string, payload: Partial<Application>) {
    return firstValueFrom(this.http.patch<Application>(`${base}/applications/${id}`, payload));
  }
  remove(id: string) {
    return firstValueFrom(this.http.delete(`${base}/applications/${id}`));
  }
  addModule(applicationId: string, payload: Partial<ApplicationModule>) {
    return firstValueFrom(
      this.http.post<ApplicationModule>(`${base}/applications/${applicationId}/modules`, payload)
    );
  }
}

@Injectable({ providedIn: 'root' })
export class SourcesService {
  constructor(private http: HttpClient) {}

  list(filters: { status?: string; application_id?: string } = {}) {
    const params: Record<string, string> = {};
    if (filters.status) params['status_filter'] = filters.status;
    if (filters.application_id) params['application_id'] = filters.application_id;
    return firstValueFrom(this.http.get<SourceSummary[]>(`${base}/sources`, { params }));
  }
  get(id: string) {
    return firstValueFrom(this.http.get<SourceDetail>(`${base}/sources/${id}`));
  }
  upload(formData: FormData) {
    return firstValueFrom(this.http.post<SourceDetail>(`${base}/sources`, formData));
  }
  chunks(sourceId: string) {
    return firstValueFrom(this.http.get<TranscriptChunk[]>(`${base}/sources/${sourceId}/chunks`));
  }
  updateChunk(sourceId: string, chunkId: string, payload: Partial<TranscriptChunk>) {
    return firstValueFrom(
      this.http.patch<TranscriptChunk>(`${base}/sources/${sourceId}/chunks/${chunkId}`, payload)
    );
  }
  approve(id: string, note = '') {
    return firstValueFrom(this.http.post<SourceDetail>(`${base}/sources/${id}/approve`, { note }));
  }
  archive(id: string) {
    return firstValueFrom(this.http.post<SourceDetail>(`${base}/sources/${id}/archive`, {}));
  }
  remove(id: string) {
    return firstValueFrom(this.http.delete(`${base}/sources/${id}`));
  }
}

@Injectable({ providedIn: 'root' })
export class AssistantService {
  constructor(private http: HttpClient) {}

  ask(payload: {
    question: string;
    application_id?: string | null;
    conversation_id?: string | null;
    application_version?: string | null;
    environment?: string | null;
  }) {
    return firstValueFrom(this.http.post<AskResponse>(`${base}/assistant/ask`, payload));
  }
  feedback(message_id: string, rating: 'helpful' | 'not_helpful', comment = '') {
    return firstValueFrom(
      this.http.post<FeedbackEntry>(`${base}/assistant/feedback`, { message_id, rating, comment })
    );
  }
  listFeedback() {
    return firstValueFrom(this.http.get<FeedbackEntry[]>(`${base}/assistant/feedback`));
  }
}

@Injectable({ providedIn: 'root' })
export class UsageService {
  constructor(private http: HttpClient) {}

  summary(days = 30) {
    return firstValueFrom(this.http.get<UsageSummary>(`${base}/usage/summary`, { params: { days } }));
  }
}

@Injectable({ providedIn: 'root' })
export class AuditService {
  constructor(private http: HttpClient) {}

  list(limit = 100) {
    return firstValueFrom(this.http.get<AuditLogEntry[]>(`${base}/audit-log`, { params: { limit } }));
  }
}
