import { Router } from 'express';
import { getLatestNews, getNewsByCategory, getNewsById, triggerCrawl } from '../controllers/news.controller.js';

const router = Router();

router.get('/latest', getLatestNews);
router.get('/category/:category', getNewsByCategory);
router.get('/:id', getNewsById);
router.post('/crawl', triggerCrawl);

export default router;
