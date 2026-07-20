export interface Token {
  access_token: string;
  refresh_token: string;
  token_type: string;
}

export interface Role {
  id: string;
  name: string;
  description: string | null;
  created_at: string;
  updated_at: string;
}

export interface Application {
  id: string;
  slug: string;
  name: string;
  description: string | null;
  is_active: boolean;
  created_at: string;
  updated_at: string;
}

export interface User {
  id: string;
  email: string;
  full_name: string | null;
  is_active: boolean;
  is_superuser: boolean;
  is_verified: boolean;
  roles: Role[];
  applications: Application[];
  created_at: string;
  updated_at: string;
}

export interface UserListItem {
  id: string;
  email: string;
  full_name: string | null;
  is_active: boolean;
  is_superuser: boolean;
  is_verified: boolean;
}
