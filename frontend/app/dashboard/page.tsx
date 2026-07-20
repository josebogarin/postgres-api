/**
 * Página del Dashboard
 */

'use client';

import { useEffect, useState } from 'react';
import { useProtectedRoute } from '@/lib/use-protected-route';
import { useAuth } from '@/lib/auth-context';
import { apiClient, ApplicationResponse, PaginatedResponse, UserResponse } from '@/lib/api-client';
import Link from 'next/link';

export default function DashboardPage() {
  const { isLoading } = useProtectedRoute();
  const { user } = useAuth();

  const [stats, setStats] = useState({
    totalApplications: 0,
    totalUsers: 0,
    isLoading: true,
  });

  const [recentApps, setRecentApps] = useState<ApplicationResponse[]>([]);

  useEffect(() => {
    const loadStats = async () => {
      try {
        const [appsResponse, usersResponse] = await Promise.all([
          apiClient.listApplications(0, 1000),
          apiClient.listUsers(0, 1000),
        ]);

        setStats({
          totalApplications: appsResponse.total,
          totalUsers: usersResponse.total,
          isLoading: false,
        });

        setRecentApps(appsResponse.items.slice(0, 5));
      } catch (error) {
        console.error('Error loading stats:', error);
        setStats((prev) => ({ ...prev, isLoading: false }));
      }
    };

    loadStats();
  }, []);

  if (isLoading) {
    return (
      <div className="flex items-center justify-center min-h-screen">
        <div className="text-gray-500">Cargando...</div>
      </div>
    );
  }

  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
      {/* Header */}
      <div className="mb-8">
        <h1 className="text-3xl font-bold text-gray-900">Dashboard</h1>
        <p className="text-gray-600 mt-2">Bienvenido, {user?.full_name || user?.email}</p>
      </div>

      {/* Stats Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6 mb-8">
        {/* Applications Card */}
        <div className="bg-white rounded-lg shadow-md p-6">
          <div className="flex justify-between items-start">
            <div>
              <p className="text-gray-500 text-sm font-medium">Aplicaciones Totales</p>
              <p className="text-3xl font-bold text-gray-900 mt-2">{stats.totalApplications}</p>
            </div>
            <div className="text-4xl">📱</div>
          </div>
        </div>

        {/* Users Card */}
        <div className="bg-white rounded-lg shadow-md p-6">
          <div className="flex justify-between items-start">
            <div>
              <p className="text-gray-500 text-sm font-medium">Usuarios Totales</p>
              <p className="text-3xl font-bold text-gray-900 mt-2">{stats.totalUsers}</p>
            </div>
            <div className="text-4xl">👥</div>
          </div>
        </div>
      </div>

      {/* Quick Actions */}
      <div className="bg-white rounded-lg shadow-md p-6 mb-8">
        <h2 className="text-xl font-bold text-gray-900 mb-4">Acciones Rápidas</h2>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          <Link
            href="/applications/new"
            className="bg-blue-600 hover:bg-blue-700 text-white px-4 py-3 rounded-lg font-medium transition text-center"
          >
            ➕ Nueva Aplicación
          </Link>
          <Link
            href="/users/new"
            className="bg-green-600 hover:bg-green-700 text-white px-4 py-3 rounded-lg font-medium transition text-center"
          >
            ➕ Nuevo Usuario
          </Link>
          <Link
            href="/applications"
            className="bg-gray-600 hover:bg-gray-700 text-white px-4 py-3 rounded-lg font-medium transition text-center"
          >
            📋 Ver Aplicaciones
          </Link>
        </div>
      </div>

      {/* Recent Applications */}
      <div className="bg-white rounded-lg shadow-md overflow-hidden">
        <div className="px-6 py-4 border-b border-gray-200">
          <h2 className="text-xl font-bold text-gray-900">Aplicaciones Recientes</h2>
        </div>

        {recentApps.length > 0 ? (
          <div className="overflow-x-auto">
            <table className="w-full">
              <thead className="bg-gray-50">
                <tr>
                  <th className="px-6 py-3 text-left text-sm font-semibold text-gray-700">Nombre</th>
                  <th className="px-6 py-3 text-left text-sm font-semibold text-gray-700">Slug</th>
                  <th className="px-6 py-3 text-left text-sm font-semibold text-gray-700">Estado</th>
                  <th className="px-6 py-3 text-left text-sm font-semibold text-gray-700">Acciones</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-200">
                {recentApps.map((app) => (
                  <tr key={app.id} className="hover:bg-gray-50">
                    <td className="px-6 py-4 text-sm text-gray-900">{app.name}</td>
                    <td className="px-6 py-4 text-sm text-gray-600">{app.slug}</td>
                    <td className="px-6 py-4 text-sm">
                      <span
                        className={`px-3 py-1 rounded-full text-xs font-medium ${
                          app.is_active
                            ? 'bg-green-100 text-green-800'
                            : 'bg-gray-100 text-gray-800'
                        }`}
                      >
                        {app.is_active ? '✓ Activo' : 'Inactivo'}
                      </span>
                    </td>
                    <td className="px-6 py-4 text-sm">
                      <Link
                        href={`/applications/${app.id}`}
                        className="text-blue-600 hover:text-blue-700 font-medium"
                      >
                        Ver
                      </Link>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        ) : (
          <div className="px-6 py-8 text-center text-gray-500">
            <p>No hay aplicaciones registradas</p>
            <Link href="/applications/new" className="text-blue-600 hover:text-blue-700 mt-2 inline-block">
              Crear la primera aplicación
            </Link>
          </div>
        )}
      </div>
    </div>
  );
}
