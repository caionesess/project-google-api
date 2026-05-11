import { Controller, Get, Param, Res, HttpException, HttpStatus } from '@nestjs/common';
import type { Response } from 'express';
import { GoogleDocsService } from './google-docs.service';

@Controller('google-docs')
export class GoogleDocsController {
  constructor(private readonly googleDocsService: GoogleDocsService) {}

  /**
   * Endpoint para baixar um documento do Google Docs em HTML
   * @param documentId ID do documento do Google Docs
   * @param res Response do Express para enviar o arquivo
   */
  @Get(':documentId/html')
  async downloadAsHtml(
    @Param('documentId') documentId: string,
    @Res() res: Response,
  ): Promise<void> {
    try {
      if (!documentId) {
        throw new HttpException('ID do documento é obrigatório', HttpStatus.BAD_REQUEST);
      }

      const html = await this.googleDocsService.getDocumentAsHtml(documentId);

      res.setHeader('Content-Type', 'text/html; charset=utf-8');
      res.setHeader('Content-Disposition', `attachment; filename="documento-${documentId}.html"`);
      res.send(html);
    } catch (error) {
      throw new HttpException(
        error.message || 'Erro ao processar documento',
        error.status || HttpStatus.INTERNAL_SERVER_ERROR,
      );
    }
  }

  /**
   * Endpoint para visualizar um documento do Google Docs em HTML no navegador
   * @param documentId ID do documento do Google Docs
   * @param res Response do Express para enviar o HTML
   */
  @Get(':documentId')
  async viewAsHtml(
    @Param('documentId') documentId: string,
    @Res() res: Response,
  ): Promise<void> {
    try {
      if (!documentId) {
        throw new HttpException('ID do documento é obrigatório', HttpStatus.BAD_REQUEST);
      }

      const html = await this.googleDocsService.getDocumentAsHtml(documentId);

      res.setHeader('Content-Type', 'text/html; charset=utf-8');
      res.send(html);
    } catch (error) {
      throw new HttpException(
        error.message || 'Erro ao processar documento',
        error.status || HttpStatus.INTERNAL_SERVER_ERROR,
      );
    }
  }
}

