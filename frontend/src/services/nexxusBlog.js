import { NEXXUS_BLOG_FALLBACK } from '../config/nexxusTech'
import api from './api'

export const MAX_BLOG_ARTICLES = 4

function normalizeArticle(article) {
  return {
    slug: article.slug,
    title: article.title,
    excerpt: article.excerpt,
    category: article.category,
    date: article.date,
    readTime: article.read_time ?? article.readTime,
    coverColor: article.cover_color ?? article.coverColor
  }
}

export async function fetchNexxusBlogArticles() {
  try {
    const { data } = await api.get('/system/nexxus-blog', { timeout: 10000 })
    if (!Array.isArray(data) || data.length === 0) {
      throw new Error('Blog API returned no articles')
    }
    return data.slice(0, MAX_BLOG_ARTICLES).map(normalizeArticle)
  } catch {
    return NEXXUS_BLOG_FALLBACK.slice(0, MAX_BLOG_ARTICLES).map(normalizeArticle)
  }
}
