export interface DossierSummary {
  id: number;
  plate: string;
  offer_id?: number;
  sold_buyer_id?: number;
  status?: string;
  created_at?: string;
  updated_at?: string;
}

export interface DossierOffer {
  id: number;
  code?: string;
  title?: string;
  brand?: string;
  model?: string;
  year?: string;
  color?: string;
  mileage?: string;
  price?: number;
  description?: string;
  status?: string;
  negotiation_status?: string;
  negotiation_substatus?: string;
  negotiation_buyer_id?: number;
  sold_buyer_id?: number;
  sold_at?: string;
  sale_notes?: string;
  finalized_at?: string;
  plate?: string;
  images?: string;
  selected_images?: string;
  processed_images?: string;
  original_images?: string;
  created_at?: string;
}

export interface DossierBuyer {
  id: number;
  name: string;
  phone?: string;
  email?: string;
}

export interface DossierConsultation {
  id: number;
  plate: string;
  source?: string;
  success?: boolean;
  result?: Record<string, unknown>;
  error_message?: string;
  created_at?: string;
}

export interface DossierFile {
  id: number;
  dossier_id: number;
  file_type: string;
  file_name?: string;
  storage_bucket?: string;
  storage_key?: string;
  mime_type?: string;
  file_size?: number;
  is_admin_only?: boolean;
  is_released_to_buyer?: boolean;
  created_at?: string;
}

export interface DossierHistoryItem {
  id: number;
  previous_status?: string;
  new_status?: string;
  buyer_id?: number;
  observations?: string;
  created_at?: string;
}

export interface VehicleDossierDetail {
  dossier: DossierSummary;
  offer?: DossierOffer | null;
  buyer?: DossierBuyer | null;
  consultations: DossierConsultation[];
  files: DossierFile[];
  negotiation_history: DossierHistoryItem[];
}
