import {request} from './client';import {Audit} from '../types/domain';export const getAudits=()=>request<Audit[]>('/audits');
