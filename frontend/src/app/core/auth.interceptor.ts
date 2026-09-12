import { HttpInterceptorFn } from '@angular/common/http';
import { inject } from '@angular/core';
import { catchError, switchMap, throwError } from 'rxjs';
import { AuthService } from './auth.service';

export const authInterceptor: HttpInterceptorFn = (request, next) => {
  const auth = inject(AuthService);
  const token = localStorage.getItem('access_token');
  const authenticatedRequest = token
    ? request.clone({ setHeaders: { Authorization: `Bearer ${token}` } })
    : request;

  return next(authenticatedRequest).pipe(
    catchError(error => {
      const refreshToken = localStorage.getItem('refresh_token');
      const isAuthRequest = request.url.includes('/auth/');
      if (error.status !== 401 || !refreshToken || isAuthRequest) {
        return throwError(() => error);
      }

      return auth.refresh().pipe(
        switchMap(() => {
          const newToken = auth.getToken();
          return next(newToken
            ? request.clone({ setHeaders: { Authorization: `Bearer ${newToken}` } })
            : request);
        }),
        catchError(refreshError => {
          auth.logout();
          return throwError(() => refreshError);
        })
      );
    })
  );
};
