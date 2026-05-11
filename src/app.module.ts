import { Module } from '@nestjs/common';
import { ConfigModule } from '@nestjs/config';
import { AppController } from './app.controller';
import { AppService } from './app.service';
import { GoogleDocsModule } from './google-docs/google-docs.module';
import { GoogleDriveModule } from './google-drive/google-drive.module';

@Module({
  imports: [
    ConfigModule.forRoot({
      isGlobal: true,
      envFilePath: '.env',
    }),
    GoogleDocsModule,
    GoogleDriveModule,
  ],
  controllers: [AppController],
  providers: [AppService],
})
export class AppModule {}
