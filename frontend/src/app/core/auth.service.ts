import { Injectable, inject } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Router } from '@angular/router';
import { Observable, tap } from 'rxjs';
import { LoginResponse, User } from '../models';

@Injectable({ providedIn: 'root' })
export class AuthService {
  private readonly http = inject(HttpClient);
  private readonly router = inject(Router);
  private readonly apiUrl = '/api';

  login(email: string, password: string): Observable<LoginResponse> {
    return this.http.post<LoginResponse>(`${this.apiUrl}/auth/login`, { email, password }).pipe(
      tap(response => localStorage.setItem('access_token', response.access_token))
    );
  }

  register(email: string, password: string): Observable<LoginResponse> {
    return this.http.post<LoginResponse>(`${this.apiUrl}/auth/register`, { email, password }).pipe(
      tap(response => localStorage.setItem('access_token', response.access_token))
    );
  }

  getToken(): string | null { return localStorage.getItem('access_token'); }
  isLoggedIn(): boolean { return !!this.getToken(); }
  getMe(): Observable<User> { return this.http.get<User>(`${this.apiUrl}/auth/me`); }

  logout(): void {
    localStorage.removeItem('access_token');
    void this.router.navigate(['/login']);
  }
}
