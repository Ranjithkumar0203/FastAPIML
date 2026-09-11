import { Component, inject } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { Router } from '@angular/router';
import { AuthService } from '../core/auth.service';

@Component({
  selector: 'app-login',
  standalone: true,
  imports: [FormsModule],
  templateUrl: './login.component.html',
  styleUrl: './login.component.css'
})
export class LoginComponent {
  private readonly auth = inject(AuthService);
  private readonly router = inject(Router);

  email = '';
  password = '';
  error = '';
  loading = false;
  registerMode = false;

  submit(): void {
    this.error = '';
    this.loading = true;
    const request = this.registerMode ? this.auth.register(this.email, this.password) : this.auth.login(this.email, this.password);
    request.subscribe({
      next: () => { this.loading = false; void this.router.navigate(['/chat']); },
      error: (error: { error?: { detail?: string } }) => {
        this.loading = false;
        this.error = error?.error?.detail ?? 'Authentication failed';
      }
    });
  }

  toggleMode(): void { this.registerMode = !this.registerMode; this.error = ''; }
}
