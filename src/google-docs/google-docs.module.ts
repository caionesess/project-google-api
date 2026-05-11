import { Module } from '@nestjs/common';
import { ConfigModule } from '@nestjs/config';
import { GoogleDocsService } from './google-docs.service';
import { GoogleDocsController } from './google-docs.controller';

@Module({
  imports: [ConfigModule],
  controllers: [GoogleDocsController],
  providers: [GoogleDocsService],
  exports: [GoogleDocsService],
})
export class GoogleDocsModule {}

