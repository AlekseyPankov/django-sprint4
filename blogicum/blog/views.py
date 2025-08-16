import datetime

from django.shortcuts import get_object_or_404, render, redirect
from django.views.generic import (
    CreateView, DeleteView, DetailView, ListView, UpdateView
)
from django.contrib.auth.models import User
from django.core.paginator import Paginator
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.urls import reverse_lazy
from django.db.models import Q, Count
from django.contrib.auth.decorators import login_required


from blog.models import Post, Category, Comments
from .forms import CommentsForm, PostForm, ProfileEditForm


class OnlyAuthorMixin(UserPassesTestMixin):

    def test_func(self):
        object = self.get_object()
        return object.author == self.request.user

    def handle_no_permission(self):
        return redirect('blog:post_detail', pk=self.get_object().pk)


def get_visible_posts():
    now = datetime.datetime.now()
    objects = Post.objects.select_related(
        'category', 'location'
    ).annotate(comment_count=Count('comments')
               ).order_by('-pub_date').filter(is_published=True, 
                                              pub_date__lte=now,
                                              category__is_published=True)
    return objects


def visible_to_user(user, author):
    now = datetime.datetime.now()
    objects = Post.objects.select_related(
        'category', 'location'
    ).annotate(comment_count=Count('comments')
               ).order_by('-pub_date')
    if user == author:
        return objects
    elif user.is_authenticated:
        return objects.filter(
            Q(is_published=True, pub_date__lte=now,
              category__is_published=True
              ) | Q(author=user)
        )
    else:
        return objects.filter(is_published=True, pub_date__lte=now,
                              category__is_published=True
                              )


class IndexListView(ListView):
    model = Post
    template_name = 'blog/index.html'    
    paginate_by = 10    
    objects = get_visible_posts()

    def get_queryset(self):
        return self.objects


class PostDetailView(DetailView):
    model = Post
    template_name = 'blog/detail.html'
    context_object_name = 'post'

    def get_object(self, queryset=None):
        post = get_object_or_404(self.model, id=self.kwargs[self.pk_url_kwarg])
        if post.author == self.request.user:
            return post
        return get_object_or_404(
            visible_to_user(self.request.user, post.author),
            id=self.kwargs[self.pk_url_kwarg],
        )

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['form'] = CommentsForm()
        context['comments'] = (
            self.object.comments.select_related('author')
        )
        return context


def category_posts(request, category_slug):
    template = 'blog/category.html'
    category = get_object_or_404(
        Category,
        slug=category_slug,
        is_published=True
    )
    post = get_visible_posts().filter(
        category__slug=category_slug,
    )
    paginator = Paginator(post, 10)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    context = {
        'category': category,
        'page_obj': page_obj
    }
    return render(request, template, context)


def profile(request, username):
    template = 'blog/profile.html'
    profile_user = get_object_or_404(User, username=username)
    if request.user == profile_user or request.user.is_superuser:
        post_list = Post.objects.filter(
            author=profile_user).annotate(
                comment_count=Count('comments')).order_by('-pub_date')
    else:
        post_list = visible_to_user(
            request.user, get_object_or_404(User, username=username)).filter(
                author=profile_user)
    paginator = Paginator(post_list, 10)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    context = {
        'profile': profile_user,
        'page_obj': page_obj
    }
    return render(request, template, context) 


class PostCreateView(LoginRequiredMixin, CreateView):
    model = Post
    form_class = PostForm
    template_name = 'blog/create.html'

    def get_success_url(self):
        return reverse_lazy(
            'blog:profile',
            kwargs={'username': self.request.user.username}
        )

    def form_valid(self, form):
        form.instance.author = self.request.user
        return super().form_valid(form)


@login_required
def edit_profile(request):
    template = 'blog/user.html'
    if request.method == 'POST':
        form = ProfileEditForm(request.POST or None, instance=request.user)
        if form.is_valid():
            form.save()
            return redirect('blog:profile', username=request.user.username)
    else:
        form = ProfileEditForm(instance=request.user)
    context = {'form': form}
    return render(request, template, context)


@login_required
def add_comment(request, post_id):
    post = get_object_or_404(Post, pk=post_id)
    if request.method == "POST":
        form = CommentsForm(request.POST)
        if form.is_valid():
            comment = form.save(commit=False)
            comment.author = request.user
            comment.post = post
            comment.save()
            return redirect('blog:post_detail', pk=post_id)


class PostDeleteView(OnlyAuthorMixin, DeleteView):
    model = Post
    template_name = 'blog/create.html'
    success_url = reverse_lazy('blog:index')


@login_required
def edit_comment(request, post_id, comment_id):
    comment = get_object_or_404(Comments, pk=comment_id)
    if comment.author != request.user:
        return redirect('blog:post_detail', pk=post_id)
    form = CommentsForm(request.POST or None, instance=comment)
    if form.is_valid():
        form.save()
        return redirect('blog:post_detail', pk=post_id)

    context = {
        'comment': comment,
        'form': form
    }
    return render(request, 'blog/comment.html', context)


@login_required
def delete_comment(request, post_id, comment_id):
    comment = get_object_or_404(Comments, pk=comment_id)
    if comment.author != request.user:
        return redirect('blog:post_detail', pk=post_id)
    if request.method == 'POST':
        comment.delete()
        return redirect('blog:post_detail', pk=post_id)
    context = {
        'comment': comment,
    }
    return render(request, 'blog/comment.html', context)


class PostUpdateView(OnlyAuthorMixin, UpdateView):
    model = Post
    form_class = PostForm
    template_name = 'blog/create.html'

    def get_success_url(self):
        return reverse_lazy(
            'blog:post_detail',
            kwargs={'pk': self.object.pk}
        )
