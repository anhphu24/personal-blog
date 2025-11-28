from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse_lazy
from django.db.models import Q
from django.core.mail import send_mail
from django.conf import settings

from django.views.generic import (
    ListView, DetailView, TemplateView, FormView
)

from .models import Post
from .forms import CommentForm, ContactForm


# ==========================
# 1. トップページ（IndexView）
# ==========================
class IndexView(ListView):
    model = Post
    template_name = 'blog/index.html'
    context_object_name = 'posts'

    def get_queryset(self):
        # Chỉ lấy bài publish, sort mới nhất, giới hạn 5 bài
        return Post.objects.filter(status='published').order_by('-created_at')[:5]


# ==========================
# 2. 記事一覧ページ (ListView)
# ==========================
class PostListView(ListView):
    model = Post
    template_name = 'blog/post_list.html'
    context_object_name = 'posts'
    paginate_by = 5  # 5 bài trên 1 trang

    def get_queryset(self):
        queryset = Post.objects.filter(status='published')

        query = self.request.GET.get('q')
        tag = self.request.GET.get('tag')

        if query:
            queryset = queryset.filter(
                Q(title__icontains=query) |
                Q(body__icontains=query)
            )

        if tag:
            queryset = queryset.filter(tags__icontains=tag)

        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['query'] = self.request.GET.get('q', '')
        context['tag'] = self.request.GET.get('tag', '')
        return context


# ==========================
# 3. 記事詳細ページ＋コメント投稿
# ==========================
class PostDetailView(DetailView):
    model = Post
    template_name = 'blog/post_detail.html'
    context_object_name = 'post'

    def get_object(self, queryset=None):
        slug = self.kwargs.get('slug')
        return get_object_or_404(Post, slug=slug, status='published')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        post = self.get_object()
        context['comments'] = post.comments.filter(active=True)
        context['form'] = CommentForm()
        return context

    def post(self, request, *args, **kwargs):
        self.object = self.get_object()
        form = CommentForm(request.POST)

        if form.is_valid():
            new_comment = form.save(commit=False)
            new_comment.post = self.object
            new_comment.save()

        return redirect('blog:post_detail', slug=self.object.slug)


# ==========================
# 4. プロフィールページ
# ==========================
class ProfileView(TemplateView):
    template_name = 'blog/profile.html'


# ==========================
# 5. お問い合わせページ (Contact)
# ==========================
class ContactView(FormView):
    template_name = 'blog/contact.html'
    form_class = ContactForm
    success_url = reverse_lazy('blog:contact')

    def form_valid(self, form):
        # 1. Lưu xuống database
        contact = form.save()

        # 2. Gửi email đến Gmail của bạn
        subject = f"[My Blog] お問い合わせ: {contact.subject}"
        message = (
            f"お名前: {contact.name}\n"
            f"メール: {contact.email}\n\n"
            f"メッセージ:\n{contact.body}"
        )

        send_mail(
            subject,
            message,
            settings.DEFAULT_FROM_EMAIL,
            [settings.EMAIL_HOST_USER],  # người nhận email
            fail_silently=False,
        )

        # 3. Bật flag để show thông báo "送信完了"
        self.request.session['contact_sent'] = True

        return super().form_valid(form)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        sent = self.request.session.pop('contact_sent', False)
        context['sent'] = sent
        return context
