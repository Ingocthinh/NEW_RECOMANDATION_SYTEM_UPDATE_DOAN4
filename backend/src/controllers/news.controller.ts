import type { Request, Response } from 'express';
import prisma from '../services/db.service.js';

export const getLatestNews = async (req: Request, res: Response) => {
    try {
        // Get distinct categories
        const categories = await prisma.news.findMany({
            select: { category: true },
            distinct: ['category'],
        });
        // Fetch latest articles from each category
        const allNews = await Promise.all(
            categories.map(c =>
                prisma.news.findMany({
                    where: { category: c.category },
                    orderBy: { published_at: 'desc' },
                    take: 8,
                })
            )
        );
        // Interleave: round-robin from each category
        const maxLen = Math.max(...allNews.map(a => a.length));
        const mixed: any[] = [];
        for (let i = 0; i < maxLen; i++) {
            for (const catArticles of allNews) {
                if (i < catArticles.length) mixed.push(catArticles[i]);
            }
        }
        res.json(mixed);
    } catch (error) {
        res.status(500).json({ error: 'Failed to fetch news' });
    }
};

export const getNewsByCategory = async (req: Request, res: Response) => {
    const { category } = req.params;
    try {
        const news = await prisma.news.findMany({
            where: { category: category as string },
            orderBy: { published_at: 'desc' },
        });
        res.json(news);
    } catch (error) {
        res.status(500).json({ error: 'Failed to fetch news by category' });
    }
};

export const getNewsById = async (req: Request, res: Response) => {
    const { id } = req.params;
    try {
        const article = await prisma.news.findUnique({
            where: { id: parseInt(id) },
        });
        if (!article) {
            return res.status(404).json({ error: 'News article not found' });
        }
        res.json(article);
    } catch (error) {
        res.status(500).json({ error: 'Failed to fetch article details' });
    }
};

export const triggerCrawl = async (req: Request, res: Response) => {
    // This will eventually call the Python crawler service
    res.json({ message: 'Crawl triggered successfully' });
};
