import {request} from './client';import {Delivery} from '../types/domain';export const getDeliveries=()=>request<Delivery[]>('/deliveries');
