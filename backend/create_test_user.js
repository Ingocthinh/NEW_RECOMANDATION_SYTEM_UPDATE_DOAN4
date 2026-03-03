import { PrismaClient } from '@prisma/client';
import bcrypt from 'bcryptjs';

const prisma = new PrismaClient();

async function main() {
    const username = 'demo_user';
    const email = 'demo@example.com';
    const password = 'password123';

    const hashedPassword = await bcrypt.hash(password, 10);

    try {
        const user = await prisma.user.upsert({
            where: { email },
            update: { password: hashedPassword },
            create: { username, email, password: hashedPassword }
        });
        console.log(`Test user created/updated: ${user.email}`);
    } catch (error) {
        console.error('Error creating test user:', error);
        process.exit(1);
    }
}

main()
    .catch(e => {
        console.error(e);
        process.exit(1);
    })
    .finally(async () => {
        await prisma.$disconnect();
    });
