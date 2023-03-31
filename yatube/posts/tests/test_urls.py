from http import HTTPStatus

from django.contrib.auth import get_user_model
from django.test import Client, TestCase
from django.urls import reverse

from posts.models import Group, Post

User = get_user_model()


class PostURLTests(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.user = User.objects.create_user(username='test_user')
        cls.group = Group.objects.create(
            title='Тестовая группа',
            slug='test-slug',
        )
        cls.post = Post.objects.create(
            text='Тестовый пост',
            author=cls.user,
            group=cls.group,
        )

    def setUp(self):
        self.guest_client = Client()
        self.user = PostURLTests.user
        self.authorized_client = Client()
        self.authorized_client.force_login(self.user)

    def test_pages_uses_correct_template(self):
        """URL-адрес использует соответствующий шаблон."""
        templates_pages_names = {
            reverse('posts:index'): 'posts/index.html',
            reverse('posts:group_list',
                    kwargs={'slug': self.group.slug}): 'posts/group_list.html',
            reverse('posts:profile',
                    kwargs={'username': self.user}): 'posts/profile.html',
            reverse('posts:post_detail', kwargs={'post_id': self.post.id}):
            'posts/post_detail.html',
            reverse('posts:post_create'): 'posts/create_post.html',
            reverse('posts:post_edit', kwargs={'post_id': self.post.id}):
            'posts/create_post.html',
            reverse('posts:follow_index'): 'posts/follow.html',
            reverse('posts:profile_follow', kwargs={'username': self.user}):
            'posts/follow.html',
            reverse('posts:profile_unfollow', kwargs={'username': self.user}):
            'posts/follow.html',
            '/unexisting_page/': 'core/404.html',
        }
        for reverse_name, template in templates_pages_names.items():
            with self.subTest(reverse_name=reverse_name):
                response = self.authorized_client.get(reverse_name)
                self.assertTemplateUsed(response, template)

    def test_url_exists_at_desired_location(self):
        """URL-адрес доступен любому пользователю."""
        pages_status_guest = {
            '/': HTTPStatus.OK,
            f'/group/{self.group.slug}/': HTTPStatus.OK,
            f'/profile/{self.user}/': HTTPStatus.OK,
            f'/posts/{self.post.id}/': HTTPStatus.OK,
            '/unexisting_page/': HTTPStatus.NOT_FOUND,
        }
        for address, status in pages_status_guest.items():
            with self.subTest(address=address):
                response = self.guest_client.get(address)
                self.assertEqual(response.status_code, status)

    def test_url_exists_at_desired_location_authorized(self):
        """URL-адрес доступен авторизированному пользователю."""
        pages_status_authorized = {
            '/': HTTPStatus.OK,
            f'/group/{self.group.slug}/': HTTPStatus.OK,
            f'/profile/{self.user}/': HTTPStatus.OK,
            f'/posts/{self.post.id}/': HTTPStatus.OK,
            f'/posts/{self.post.id}/comment/': HTTPStatus.FOUND,
            '/create/': HTTPStatus.OK,
            f'/posts/{self.post.id}/edit/': HTTPStatus.OK,
            '/follow/': HTTPStatus.OK,
            f'/profile/{self.user}/follow/': HTTPStatus.OK,
            f'/profile/{self.user}/unfollow/': HTTPStatus.OK,
            '/unexisting_page/': HTTPStatus.NOT_FOUND,
        }
        for address, status in pages_status_authorized.items():
            with self.subTest(address=address):
                response = self.authorized_client.get(address)
                self.assertEqual(response.status_code, status)

    def test_url_redirect_anonymous(self):
        """Страница перенаправит анонимного пользователяна страницу логина."""
        templates_names = [
            f'/posts/{self.post.id}/comment/',
            '/create/',
            f'/posts/{self.post.id}/edit/',
        ]
        for names in templates_names:
            response = self.guest_client.get(names, follow=True)
            self.assertRedirects(response, f'/auth/login/?next={names}')
