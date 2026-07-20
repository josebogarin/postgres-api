/**
 * Cliente HTTP para consumir la API FastAPI
 * Con manejo de tokens JWT y refresh automático
 */

export interface TokenResponse {
  access_token: string;
  refresh_token: string;
  token_type: string;
}

export interface UserResponse {
  id: string;
  email: string;
  full_name?: string;
  is_active: boolean;
  is_superuser: boolean;
  created_at: string;
  updated_at: string;
}

export interface ApplicationResponse {
  id: string;
  slug: string;
  name: string;
  description?: string;
  db_url?: string;
  is_active: boolean;
  created_at: string;
  updated_at: string;
}

export interface PaginatedResponse<T> {
  total: number;
  skip: number;
  limit: number;
  items: T[];
}

class APIClient {
  private baseUrl: string;
  private accessToken: string | null = null;
  private refreshToken: string | null = null;

  constructor(baseUrl: string = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000') {
    this.baseUrl = baseUrl;
    this.loadTokens();
  }

  private loadTokens() {
    if (typeof window !== 'undefined') {
      this.accessToken = localStorage.getItem('accessToken');
      this.refreshToken = localStorage.getItem('refreshToken');
    }
  }

  private saveTokens(accessToken: string, refreshToken: string) {
    this.accessToken = accessToken;
    this.refreshToken = refreshToken;
    if (typeof window !== 'undefined') {
      localStorage.setItem('accessToken', accessToken);
      localStorage.setItem('refreshToken', refreshToken);
    }
  }

  private clearTokens() {
    this.accessToken = null;
    this.refreshToken = null;
    if (typeof window !== 'undefined') {
      localStorage.removeItem('accessToken');
      localStorage.removeItem('refreshToken');
    }
  }

  private async request<T>(
    endpoint: string,
    options: RequestInit = {}
  ): Promise<T> {
    const url = `${this.baseUrl}/api/v1${endpoint}`;

    const headers: HeadersInit = {
      'Content-Type': 'application/json',
      ...options.headers,
    };

    if (this.accessToken) {
      headers['Authorization'] = `Bearer ${this.accessToken}`;
    }

    try {
      let response = await fetch(url, {
        ...options,
        headers,
      });

      // Si obtenemos 401, intentar refrescar token
      if (response.status === 401 && this.refreshToken) {
        try {
          await this.refreshAccessToken();
          // Reintentar con nuevo token
          headers['Authorization'] = `Bearer ${this.accessToken}`;
          response = await fetch(url, {
            ...options,
            headers,
          });
        } catch (error) {
          this.clearTokens();
          throw new Error('Session expired. Please login again.');
        }
      }

      if (!response.ok) {
        const error = await response.json().catch(() => ({ detail: response.statusText }));
        throw new Error(error.detail || response.statusText);
      }

      return response.json() as Promise<T>;
    } catch (error) {
      throw error;
    }
  }

  // ==================== AUTENTICACIÓN ====================

  async login(email: string, password: string): Promise<TokenResponse> {
    const response = await this.request<TokenResponse>('/auth/login', {
      method: 'POST',
      body: JSON.stringify({ email, password }),
    });

    this.saveTokens(response.access_token, response.refresh_token);
    return response;
  }

  async refreshAccessToken(): Promise<TokenResponse> {
    if (!this.refreshToken) {
      throw new Error('No refresh token available');
    }

    const response = await this.request<TokenResponse>('/auth/refresh', {
      method: 'POST',
      body: JSON.stringify({ refresh_token: this.refreshToken }),
    });

    this.saveTokens(response.access_token, response.refresh_token);
    return response;
  }

  async getCurrentUser(): Promise<UserResponse> {
    return this.request<UserResponse>('/auth/me');
  }

  logout() {
    this.clearTokens();
  }

  isAuthenticated(): boolean {
    return this.accessToken !== null;
  }

  // ==================== APLICACIONES ====================

  async listApplications(skip: number = 0, limit: number = 100): Promise<PaginatedResponse<ApplicationResponse>> {
    return this.request<PaginatedResponse<ApplicationResponse>>(
      `/applications?skip=${skip}&limit=${limit}`
    );
  }

  async getApplication(id: string): Promise<ApplicationResponse> {
    return this.request<ApplicationResponse>(`/applications/${id}`);
  }

  async createApplication(data: {
    name: string;
    slug: string;
    description?: string;
    db_url?: string;
  }): Promise<ApplicationResponse> {
    return this.request<ApplicationResponse>('/applications', {
      method: 'POST',
      body: JSON.stringify(data),
    });
  }

  async updateApplication(id: string, data: Partial<ApplicationResponse>): Promise<ApplicationResponse> {
    return this.request<ApplicationResponse>(`/applications/${id}`, {
      method: 'PATCH',
      body: JSON.stringify(data),
    });
  }

  async deleteApplication(id: string): Promise<void> {
    await this.request('/applications/' + id, {
      method: 'DELETE',
    });
  }

  // ==================== USUARIOS ====================

  async listUsers(skip: number = 0, limit: number = 100): Promise<PaginatedResponse<UserResponse>> {
    return this.request<PaginatedResponse<UserResponse>>(
      `/users?skip=${skip}&limit=${limit}`
    );
  }

  async getUser(id: string): Promise<UserResponse> {
    return this.request<UserResponse>(`/users/${id}`);
  }

  async createUser(data: {
    email: string;
    password: string;
    full_name?: string;
  }): Promise<UserResponse> {
    return this.request<UserResponse>('/users', {
      method: 'POST',
      body: JSON.stringify(data),
    });
  }

  async updateUser(id: string, data: Partial<UserResponse>): Promise<UserResponse> {
    return this.request<UserResponse>(`/users/${id}`, {
      method: 'PATCH',
      body: JSON.stringify(data),
    });
  }

  async deleteUser(id: string): Promise<void> {
    await this.request(`/users/${id}`, {
      method: 'DELETE',
    });
  }

  // ==================== AUDITORÍA ====================

  async listAuditLogs(skip: number = 0, limit: number = 100): Promise<PaginatedResponse<any>> {
    return this.request<PaginatedResponse<any>>(
      `/audit-logs?skip=${skip}&limit=${limit}`
    );
  }

  // ==================== HEALTH ====================

  async healthCheck(): Promise<{ status: string }> {
    return this.request<{ status: string }>('/health');
  }
}

// Exportar instancia singleton
export const apiClient = new APIClient();
