import { ChangeDetectorRef, Component, ElementRef, OnInit, ViewChild, inject } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { Router } from '@angular/router';
import { AuthService } from '../core/auth.service';
import { ChatMessage, Thread } from '../models';
import { ChatService } from '../services/chat.service';
import { ThreadService } from '../services/thread.service';

@Component({
  selector: 'app-chat',
  standalone: true,
  imports: [CommonModule, FormsModule],
  templateUrl: './chat.component.html',
  styleUrl: './chat.component.css'
})
export class ChatComponent implements OnInit {
  @ViewChild('messagesContainer') private messagesContainer?: ElementRef<HTMLElement>;

  private readonly threadService = inject(ThreadService);
  private readonly chatService = inject(ChatService);
  private readonly auth = inject(AuthService);
  private readonly router = inject(Router);
  private readonly cdr = inject(ChangeDetectorRef);

  threads: Thread[] = [];
  messages: ChatMessage[] = [];
  currentThreadId: string | null = null;
  currentThreadTitle = 'New Chat';
  messageText = '';
  loading = false;
  loadingThreads = false;
  userEmail = '';

  ngOnInit(): void { this.loadUser(); this.loadThreads(); }

  loadUser(): void { this.auth.getMe().subscribe({ next: user => this.userEmail = user.email }); }

  loadThreads(): void {
    this.loadingThreads = true;
    this.threadService.getThreads().subscribe({
      next: threads => {
        this.threads = threads;
        this.loadingThreads = false;
        if (threads.length > 0) this.selectThread(threads[0]); else this.createNewChat();
      },
      error: () => this.loadingThreads = false
    });
  }

  createNewChat(): void {
    this.threadService.createThread().subscribe({
      next: thread => {
        this.currentThreadId = thread.id;
        this.currentThreadTitle = thread.title;
        this.messages = [];
        this.loadThreads();
      }
    });
  }

  selectThread(thread: Thread): void {
    this.currentThreadId = thread.id;
    this.currentThreadTitle = thread.title;
    this.messages = [];
    this.threadService.getMessages(thread.id).subscribe({ next: messages => { this.messages = messages; this.scrollToBottom(); } });
  }

  sendMessage(): void {
    const text = this.messageText.trim();
    if (!text || !this.currentThreadId || this.loading) return;
    this.messages.push({ role: 'user', content: text });
    this.messageText = '';
    this.loading = true;
    this.scrollToBottom();
    this.chatService.sendMessage(this.currentThreadId, text).subscribe({
      next: response => {
        this.messages.push({ role: 'assistant', content: response.message });
        this.loading = false;
        this.loadThreads();
        this.scrollToBottom();
      },
      error: (error: unknown) => {
        this.loading = false;
        this.messages.push({ role: 'assistant', content: 'Sorry, something went wrong.' });
        console.error(error);
      }
    });
  }

  resetChat(): void { this.createNewChat(); }
  logout(): void { this.auth.logout(); }

  deleteThread(event: Event, thread: Thread): void {
    event.stopPropagation();
    this.threadService.deleteThread(thread.id).subscribe({
      next: () => {
        if (this.currentThreadId === thread.id) { this.currentThreadId = null; this.messages = []; }
        this.loadThreads();
      }
    });
  }

  onEnter(event: Event): void {
    const keyboardEvent = event as KeyboardEvent;
    if (keyboardEvent.key !== 'Enter') return;
    if (keyboardEvent.shiftKey) return;
    keyboardEvent.preventDefault();
    this.sendMessage();
  }

  trackByThread(index: number, thread: Thread): string { return thread.id; }
  trackByMessage(index: number): number { return index; }

  scrollToBottom(): void {
    setTimeout(() => {
      this.cdr.detectChanges();
      setTimeout(() => {
        const element = this.messagesContainer?.nativeElement;
        if (element) element.scrollTop = element.scrollHeight;
      });
    }, 50);
  }
}
